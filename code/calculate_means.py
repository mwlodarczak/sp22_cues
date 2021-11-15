#!/usr/bin/env python3

import os
import sys
import re
import csv

from glob import glob
import pandas as pd
import numpy as np
from scipy.stats import gaussian_kde

import tgt


def remove_low_peak(vq):

    pitch = vq.pitch.dropna(inplace=False)
    pitch_min, pitch_max = min(pitch), max(pitch)
    pitch_xs = np.linspace(pitch_min, pitch_max, 1000)
    dens = gaussian_kde(pitch)(pitch_xs)
    pitch_mode = np.argmax(dens)
    pitch_trough = np.argmin(dens[0:pitch_mode])
    pitch_cols = ['pitch', 'h1h2', 'hrf']
    vq.loc[vq.pitch < pitch_xs[pitch_trough], pitch_cols] = np.nan
    return vq


def read_vq(path):
    """Read and clean up the voice quality data."""

    vq = pd.read_csv(path, na_values=['NA', '--undefined--'])
    vq = remove_low_peak(vq)
    return vq[vq['vuv'] == 1]


def read_vowels(path):
    """Read vocalic boundaries"""

    tg = tgt.read_textgrid(path)
    return tg.get_tier_by_name('vowels')


def get_vq_prev(vq, vowels, ipu_start, ipu_end, frame_size):
    """Calculate pre-pausal VQ measures."""

    # Get *up to* 1 s before the pause.
    lo = max(ipu_start, ipu_end - 1)
    hi = ipu_end

    return get_vq_roi(vq, vowels, lo, hi, -1, frame_size)


def get_vq_next(vq, vowels, ipu_start, ipu_end, frame_size):
    """Calculate post-pasual VQ measures."""

    # Get *up to* 1 s after the pause.
    lo = ipu_start
    hi = min(ipu_start + 1, ipu_end)

    return get_vq_roi(vq, vowels, lo, hi, 0, frame_size)


def get_vq_roi(vq, vowels, lo, hi, vowel_ix, frame_size):

    t = np.array(vq['time'])

    v = vowels.get_annotations_between_timepoints(lo, hi, True, True)

    if v:
        v_start, v_end = v[vowel_ix].start_time, v[vowel_ix].end_time
        v_start = max(v_start + frame_size / 2, lo)
        v_end = min(v_end - frame_size / 2, hi)

        # Discard voiced intervals shorter than 20 ms (note that
        # this amounts to the total duration of at least 70 ms).
        if v_end - v_start < 0.02:
            return None

        v_vq = vq[(t >= v_start) & (t <= v_end)]
        voiced = v_vq['pitch'].dropna()
        v_pitch_st = 12 * np.log2(voiced)
        if len(v_pitch_st):
            v_pitch_range = max(v_pitch_st) - min(v_pitch_st)
            v_pitch_sd = np.std(v_pitch_st)
        else:
            v_pitch_range = np.nan
            v_pitch_sd = np.nan
        return {'roi_start': v_start,
                'roi_end': v_end,
                'roi_dur': v_end - v_start,
                'voiced_frames': len(voiced.index),
                'perc_voiced_frames': len(voiced.index) / len(v_vq.index),
                'pitch_range': v_pitch_range,
                'pitch_sd': v_pitch_sd,
                **dict(v_vq.drop('time', axis=1).median(skipna=True)),
                }
    else:
        return None


def main(vad_dir, vq_dir, vowels_dir, outdir, frame_size):

    res_all = []

    for tg_path in glob(os.path.join(vad_dir, '*_chrono.TextGrid')):

        tg_fname = os.path.basename(tg_path)
        session_id = re.match(r'[\d-]+', tg_fname).group()
        print(f'Processing {session_id}...', file=sys.stderr)

        # Read the TextGrid and store the relevant tiers.
        tg = tgt.read_textgrid(tg_path)
        chrono = tg.get_tier_by_name('chrono')
        vad = {i: tg.get_tier_by_name(i) for i in ('01', '02')}
        try:
            vq = {i: read_vq(os.path.join(vq_dir, f'{i}-{session_id}_vq.csv'))
                  for i in ('01', '02')}
        except FileNotFoundError:
            continue

        # Read "vowel" boundaries
        vowels = {i: read_vowels(os.path.join(vowels_dir, f'{i}-{session_id}_vowels.TextGrid'))
                  for i in ('01', '02')}

        for i, intr in enumerate(chrono):

            # Only process between- and within-speaker silences.
            if intr.text not in ['bss', 'wss', 'bso']:
                continue

            prev_spkr = chrono[i - 1].text
            next_spkr = chrono[i + 1].text

            # Only look at instances bounded by solo speech.
            if {prev_spkr, next_spkr} - {'01', '02'}:
                continue

            # Sanity check.
            assert (intr.text == 'wss') ^ (prev_spkr != next_spkr)

            # Fine the preceding and following intervals.
            if intr.text == 'bso':
                prev_end = intr.end_time
                next_start = intr.start_time
            else:
                prev_end = intr.start_time
                next_start = intr.end_time

            prev_ipu = vad[prev_spkr].get_annotation_by_end_time(
                prev_end)
            next_ipu = vad[next_spkr].get_annotation_by_start_time(
                next_start)

            vq_prev = get_vq_prev(vq[prev_spkr], vowels[prev_spkr], prev_ipu.start_time,
                                  intr.start_time, frame_size)
            if vq_prev is None:
                continue

            res = {
                'session_id': session_id,
                'intr_start': intr.start_time,
                'intr_end': intr.end_time,
                'intr_dur': intr.duration(),
                'intr_type': intr.text,
                'prev_spkr': f'{prev_spkr}_{session_id}',
                'next_spkr': f'{next_spkr}_{session_id}',
                'prev_dur': prev_ipu.duration(),
                'next_dur': next_ipu.duration(),
                'prev_end': prev_ipu.end_time,
                'next_start': next_ipu.start_time,
                **vq_prev
            }

            res_all.append(res)

    with open(os.path.join(outdir, 'vq.csv'), 'w') as fout:

        writer = csv.DictWriter(fout, fieldnames=res_all[0].keys())
        writer.writeheader()
        writer.writerows(res_all)


if __name__ == '__main__':
    main(*sys.argv[1:-1], float(sys.argv[-1]))
