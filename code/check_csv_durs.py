#!/usr/bin/env python3

from glob import glob
import sys
import os
import subprocess

import pandas as pd

wav_dir = sys.argv[1]
vq_dir = sys.argv[2]

for wav_path in glob(os.path.join(wav_dir, '*/0[12]*.wav')):
    wav_dur = float(subprocess.check_output(['soxi', '-D', wav_path]))
    fname = os.path.basename(wav_path).replace('.wav', '')
    vq_path = os.path.join(vq_dir, fname + '_vq.csv')

    if not os.path.exists(vq_path):
        print(f'VQ file does not exist: {os.path.basename(vq_path)}',
              file=sys.stderr)
        continue

    vq = pd.read_csv(vq_path, na_values='--undefined--')
    vq_dur = vq['time'].iloc[-1]

    if abs(wav_dur - vq_dur) > 0.5:
        print(f'Durations do not match: {fname}', file=sys.stderr)
