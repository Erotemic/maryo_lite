"""The slow first-run asset build must always show useful, accurate progress."""
from __future__ import annotations

import io
import json
import sys
import time

import pytest
from PIL import Image

from mary_o_lite.content import ASSETS, ROOT

sys.path.insert(0, str(ROOT / 'tools'))

from asset_progress import AssetProgress
from ambition_art import build as painted
from build_assets import (_LEGACY_RIGS, _LEGACY_ROBOT, _stamp_matches,
                          planned_assets, generate_art)
from compose_audio import build_audio, SOUNDS, TRACKS


def test_progress_has_total_stage_cache_and_completion():
    stream = io.StringIO()
    with AssetProgress(4, stream=stream, report_seconds=0,
                       heartbeat_seconds=0) as progress:
        progress.stage('Cosmic Mary-O')
        progress.working('transform frame 1/2')
        progress.advance(item='transform frame 1/2')
        progress.advance(item='transform frame 2/2')
        progress.stage('Animated enemies')
        progress.advance(count=2, cached=True, item='already cached')
    log = stream.getvalue()
    assert 'Preparing 4 generated assets' in log
    assert 'Cosmic Mary-O' in log
    assert 'transform frame 1/2' in log
    assert '2/4 (50%)' in log
    assert 'Complete: 4/4 (100%)' in log
    assert 'built 2, reused 2' in log


def test_progress_heartbeat_reports_slow_frame():
    stream = io.StringIO()
    with AssetProgress(1, stream=stream, heartbeat_seconds=0.015) as progress:
        progress.stage('Snake Plant')
        progress.working('emerge frame 1/1')
        time.sleep(0.07)
        progress.advance()
    assert 'still painting: 0/1' in stream.getvalue()
    assert 'emerge frame 1/1' in stream.getvalue()


def test_asset_errors_explain_resume_without_claiming_completion():
    stream = io.StringIO()
    with pytest.raises(ValueError, match='broken painter'):
        with AssetProgress(5, stream=stream, heartbeat_seconds=0) as progress:
            progress.stage('Void Lizard')
            progress.working('walk frame 3/8')
            progress.advance()
            raise ValueError('broken painter')
    log = stream.getvalue()
    assert 'FAILED at 1/5' in log
    assert 'Void Lizard: walk frame 3/8' in log
    assert 'can be reused on retry' in log
    assert 'Complete:' not in log


def test_planned_totals_cover_all_asset_families():
    svg_count = sum(len(json.loads(p.read_text())['parts'])
                    for p in (ASSETS/'rigs').glob('*.json'))
    svg_count += int((ASSETS/'svg'/'player-robot-v3.svg').is_file())
    audio_count = len(TRACKS) + len(SOUNDS)
    assert planned_assets(art=False, audio=True) == audio_count
    assert planned_assets(art=True, audio=False) == svg_count + painted.total_frames()
    assert planned_assets() == svg_count + painted.total_frames() + audio_count


def test_source_painted_frames_report_reuse_and_corruption_repair(tmp_path):
    painted_image = Image.new('RGBA', (4, 4), (50, 100, 150, 255))
    def paint(name, index, count):
        return painted_image.copy()
    with AssetProgress(3, stream=io.StringIO(), heartbeat_seconds=0) as p:
        painted._frames([('walk', 3, 90)], paint, tmp_path, p)
        assert (p.built, p.cached) == (3, 0)
    (tmp_path / 'walk' / '001.png').write_bytes(b'broken')
    with AssetProgress(3, stream=io.StringIO(), heartbeat_seconds=0) as p:
        painted._frames([('walk', 3, 90)], paint, tmp_path, p)
        assert (p.built, p.cached) == (1, 2)


def test_full_legacy_painter_cache_is_migrated_without_repainting(monkeypatch, tmp_path):
    monkeypatch.setattr(painted, 'OUTPUT', tmp_path)
    assert painted._stamp() == painted._LEGACY_PAINTER_STAMP
    # The top-level fast path checks these representative outputs.
    for relative in (
        'cosmic/transform/035.png', 'cosmic/shrink/017.png',
        'tiles/ground_top.png', 'props/super_mary_o_coin/spin/005.png',
        'enemies/void_lizard/walk/007.png', 'enemies/solid_snake/walk/007.png',
        'enemies/ai_slop/walk/007.png',
        'enemies/npc_snakes_on_a_paper_plane/fly/007.png',
        'enemies/npc_snakes_on_a_cartesian_plane/fly/007.png',
        'construction/fire_orb/idle/007.png',
        'construction/void_orb/idle/000.png',
        'construction/coconut/idle/000.png', 'birds/european_swallow.png',
        'construction/super_mary_o_lift/idle/003.png',
        'construction/super_mary_o_flag/idle/003.png',
    ):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'legacy generated data')
    marker = tmp_path / 'manifest.json'
    marker.write_text(json.dumps({'stamp': painted._LEGACY_STAMP}))
    with AssetProgress(painted.total_frames(), stream=io.StringIO(),
                       heartbeat_seconds=0) as progress:
        assert painted.generate(progress=progress) is False
        assert progress.cached == painted.total_frames()
    assert json.loads(marker.read_text())['stamp'] == painted._stamp()
    assert (tmp_path / 'cosmic/transform/035.png').read_bytes() == b'legacy generated data'
    assert not (tmp_path / '.building.json').exists()


def test_legacy_stamp_requires_unchanged_art_sources():
    assert painted._compatible_stamp(painted._LEGACY_STAMP,
                                     painted._LEGACY_PAINTER_STAMP)
    assert not painted._compatible_stamp(painted._LEGACY_STAMP, 'modified-art')
    for name, old_and_new in _LEGACY_RIGS.items():
        assert _stamp_matches(old_and_new[0], old_and_new[1], old_and_new)
        assert not _stamp_matches(old_and_new[0], 'changed-rig', old_and_new)
    assert _stamp_matches(_LEGACY_ROBOT[0], _LEGACY_ROBOT[1], _LEGACY_ROBOT)


def test_audio_progress_counts_generated_and_cached(monkeypatch, tmp_path):
    import compose_audio
    monkeypatch.setattr(compose_audio, 'song', lambda path, *_: path.write_bytes(b'track'))
    monkeypatch.setattr(compose_audio, 'effect', lambda path, *_: path.write_bytes(b'effect'))
    n = len(TRACKS) + len(SOUNDS)
    with AssetProgress(n, stream=io.StringIO(), heartbeat_seconds=0) as progress:
        build_audio(tmp_path, progress=progress)
        assert (progress.built, progress.cached) == (n, 0)
    with AssetProgress(n, stream=io.StringIO(), heartbeat_seconds=0) as progress:
        build_audio(tmp_path, progress=progress)
        assert (progress.built, progress.cached) == (0, n)


def test_legacy_svg_rig_cache_is_migrated_without_rasterizing(monkeypatch, tmp_path):
    import build_assets
    monkeypatch.setattr(build_assets, 'GENERATED', tmp_path)
    for rig_file in sorted((ASSETS/'rigs').glob('*.json')):
        rig = json.loads(rig_file.read_text())
        folder = tmp_path/'parts'/rig_file.stem
        folder.mkdir(parents=True)
        (folder/'manifest.json').write_text(json.dumps({
            'stamp': _LEGACY_RIGS[rig_file.stem][0], 'pivots': {},
        }))
        for part in rig['parts']:
            (folder/(part['name']+'.png')).write_bytes(b'original image')
    robot = tmp_path/'robot'
    robot.mkdir()
    (robot/'castle_robot.png').write_bytes(b'original robot')
    (robot/'manifest.json').write_text(json.dumps({'stamp': _LEGACY_ROBOT[0]}))
    # The original Ambition-art cache has its own compatibility test above.
    monkeypatch.setattr(painted, 'generate', lambda *, force, progress: False)
    with AssetProgress(42, stream=io.StringIO(), heartbeat_seconds=0) as p:
        generate_art(progress=p)
        assert (p.built, p.cached) == (0, 42)
    for rig_file in sorted((ASSETS/'rigs').glob('*.json')):
        marker = tmp_path/'parts'/rig_file.stem/'manifest.json'
        assert json.loads(marker.read_text())['stamp'] == _LEGACY_RIGS[rig_file.stem][1]
    assert json.loads((robot/'manifest.json').read_text())['stamp'] == _LEGACY_ROBOT[1]


def test_audio_write_is_atomic(tmp_path):
    import wave
    from compose_audio import write
    target = tmp_path/'sample.wav'
    write(target, [0.0, 0.25, -0.25, 0.0])
    with wave.open(str(target), 'rb') as opened:
        assert opened.getnframes() == 4
        assert opened.getnchannels() == 1
    assert not list(tmp_path.glob('*.tmp'))
