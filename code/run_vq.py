#!/usr/bin/env python3

import subprocess
from glob import glob
import os
import sys

data_dir = sys.argv[1]
target_dir = sys.argv[2]

for wav_path in glob(os.path.join(data_dir, '0[12]*.wav')):
    fid = os.path.basename(wav_path).replace('.wav', '')
    session_id = fid[3:]
    print(f'Processing {wav_path}', file=sys.stderr)
    if os.path.exists(os.path.join(target_dir, fid + '_vq.csv')):
        print('  CSV file exists. Skipping.', file=sys.stderr)
        continue
    subprocess.run(['praat', '--run', 'vq_slices.praat',
                    wav_path, target_dir,
                    '60', '330', '0.002', '10', '10', '7000', '10'])
