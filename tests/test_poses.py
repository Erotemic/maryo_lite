"""Authoring data, not an image strip, drives the animation sampler."""
import pytest

from mary_o_lite.poses import load_rig, sample_pose


@pytest.mark.parametrize('form,view', [('small','side'),('small','front'),('tall','side'),
                                       ('tall','front'),('fire','side'),('fire','front')])
def test_svg_part_metadata_for_each_form(form, view):
    rig=load_rig(form,view)
    assert rig['parts']
    assert rig['frame']['ground_y'] > 0
    names={p['name'] for p in rig['parts']}
    assert len(names)==len(rig['parts'])
    bones={p['bone'] for p in rig['parts']}
    for part in rig['parts']:
        assert part['pivot'] and part['include']
    for clip in rig['clips'].values():
        assert clip['ms']>0
        for frame in clip['frames']:
            assert bones <= frame.keys()
            assert all(len(frame[bone])==5 for bone in bones)


def test_all_source_motion_clips_are_present():
    small=load_rig('small')['clips']
    tall=load_rig('tall')['clips']
    fire=load_rig('fire')['clips']
    assert {'idle','walk','jump','skid','climb','swim'} <= small.keys()
    assert {'idle','walk','jump','skid','climb','swim','crouch','crouch_walk','crouch_jump'} <= tall.keys()
    assert {'shoot','climb','swim','crouch_walk'} <= fire.keys()
    assert 'death' in load_rig('small','front')['clips']


def test_poses_interpolate_and_loop():
    rig=load_rig('small')
    walk=rig['clips']['walk']
    start=sample_pose(rig,'walk',0)
    assert start==walk['frames'][0]
    half=sample_pose(rig,'walk',walk['ms']*.0005)
    joint=next(b for b in start if start[b][:4]!=walk['frames'][1][b][:4])
    assert half[joint][0:4] == pytest.approx([
        (start[joint][i]+walk['frames'][1][joint][i])/2 for i in range(4)
    ])
    loop=sample_pose(rig,'walk',walk['ms']*.001*len(walk['frames']))
    for joint in start:
        assert loop[joint]==pytest.approx(start[joint])


def test_scale_and_mirror_are_preserved():
    rig=load_rig('tall')
    scales=[v[3] for track in rig['clips'].values() for fr in track['frames'] for v in fr.values()]
    mirrors=[v[4] for track in rig['clips'].values() for fr in track['frames'] for v in fr.values()]
    assert min(scales)<1
    assert 1 in mirrors


def test_one_shot_clip_holds_and_invalid_clip_rejected():
    rig=load_rig('fire','front')
    assert sample_pose(rig,'death',100) == sample_pose(rig,'death',0)
    with pytest.raises(KeyError):sample_pose(rig,'unknown',0)
    with pytest.raises(ValueError):load_rig('invented_form')


def test_cosmic_body_is_fire_with_composed_wings():
    assert load_rig('cosmic') == load_rig('fire')
