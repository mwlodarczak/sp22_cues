#!/usr/bin/python3
# find-vowel.py -- Identify voiced intervals from VUV frames.

import sys
from glob import glob
import os

import numpy as np
import pandas as pd

import tgt


def find_vowels(time, vuv, min_dur=0):

    breaks = np.array(time[np.where(np.sign(np.diff(vuv)) != 0)[0] + 1])
    if vuv.iloc[0] != 0:
        breaks = np.insert(breaks, 0, [0])
    if len(breaks) > 0:
        return [(lo, hi) for lo, hi in zip(breaks[:-1:2], breaks[1::2])
                if hi - lo >= min_dur]
    else:
        return None


if __name__ == '__main__':

    for vq_path in glob(os.path.join(sys.argv[1], '*.csv')):
        print(f'Processing {os.path.basename(vq_path)}')
        data = pd.read_csv(vq_path, na_values=['NA', '--undefined--'])
        # vowels = find_vowels(data['time'], 0.002, 0.02, 0.005, 0.9)
        vowels = find_vowels(data['time'], data['vuv'], 0.02)
        tg = tgt.TextGrid()
        vowels_tr = tgt.IntervalTier(name='vowels')
        for v in vowels:
            vowels_tr.add_interval(tgt.Interval(v[0], v[1], 'V'))
        tg.add_tier(vowels_tr)

        fname_out = os.path.basename(vq_path).replace(
            '_vq.csv', '_vowels.TextGrid')
        output_path = os.path.join(sys.argv[2], fname_out)
        tgt.write_to_file(tg, output_path)
