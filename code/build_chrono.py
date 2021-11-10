#!/usr/env python3

from glob import glob
import csv
import os
import sys
import re

import tgt


def get_session_id(fname):
    return re.search(r'\d{6}-\d', fname).group(0)


def read_vad(path, beeps):

    fname = os.path.basename(path).replace('.TextGrid', '')
    session_id = fname[3:]
    spkr_id = fname[:2]
    print(session_id, spkr_id)

    vad = tgt.read_textgrid(path).tiers[0]
    conv_start = beeps[session_id][0]
    conv_end = beeps[session_id][1]

    # Get annotations between the beeps.
    vad = vad.get_annotations_between_timepoints(conv_start, conv_end)
    assert vad[0].start_time >= conv_start and vad[-1].end_time <= conv_end

    if set(i.text for i in vad) != {'x'}:
        raise ValueError(f'Silences present in file {fname}.')

    return tgt.IntervalTier(name=spkr_id, objects=vad)


root_dir = sys.argv[1]
beeps_path = sys.argv[2]
chrono_dir = sys.argv[3]

with open(beeps_path) as beeps_f:
    beeps = {ln['file']: (float(ln['start']) / 1000, float(ln['end']) / 1000)
             for ln in csv.DictReader(beeps_f)}

tg_paths = sorted(glob(os.path.join(root_dir, '*.TextGrid')),
                  key=get_session_id)
for tg_path1, tg_path2 in zip(tg_paths[:-1:2], tg_paths[1::2]):

    session_id1 = os.path.basename(tg_path1)[3:].replace('.TextGrid', '')
    session_id2 = os.path.basename(tg_path2)[3:].replace('.TextGrid', '')

    if session_id1 != session_id1:
        raise Exception(f'Session IDs do not match: {os.path.basename(tg_path1)} \
        {os.path.basename(tg_path2)}')

    tg_clean = tgt.TextGrid()
    tg_clean.add_tiers([read_vad(tg_path1, beeps),
                        read_vad(tg_path2, beeps)])

    # Calculate chronogram
    chrono = tgt.util.chronogram(tg_clean.tiers)
    # Strip all speaker information from [BW]S[OS] intervals.
    for intr in chrono:
        if intr.text.startswith('bs') or intr.text.startswith('ws'):
            intr.text = intr.text[:3]
    chrono.name = 'chrono'
    tg_clean.add_tier(chrono)

    outpath = os.path.join(chrono_dir,
                           f'{session_id1}_chrono.TextGrid')
    tgt.write_to_file(tg_clean, outpath)
