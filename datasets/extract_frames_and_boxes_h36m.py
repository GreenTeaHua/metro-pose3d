#!/usr/bin/env python3

import glob
import multiprocessing
import os
import pathlib
import sys

import h5py
import imageio
import numpy as np


def main():
    if 'DATA_ROOT' not in os.environ:
        print('Set the DATA_ROOT environment variable to the parent dir of the h36m directory.')
        sys.exit(1)

    pool = multiprocessing.Pool()
    data_root = os.environ['DATA_ROOT']
    bbox_paths = glob.glob(f'{data_root}/h36m/**/ground_truth_bb/*.mat', recursive=True)
    pool.map(extract_bounding_boxes, bbox_paths)

    video_paths = glob.glob(f'{data_root}/h36m/**/Videos/*.mp4', recursive=True)
    pool.map(extract_frames, video_paths)


def extract_bounding_boxes(src_matfile_path):
    """Human3.6M supplies bounding boxes in the form of masks with 1s inside the box and 0s
    outside. This converts from that format to NumPy files containing the bounding box coordinates
    in [left, top, width, height] representation.
    """
    print('Processing', src_matfile_path)
    with h5py.File(src_matfile_path, 'r') as f:
        refs = f['Masks'][:, 0]
        bboxes = np.empty([len(refs), 4], dtype=np.float32)
        for i, ref in enumerate(refs):
            mask = np.array(f['#refs#'][ref]).T
            try:
                xmin, xmax = np.nonzero(np.any(mask, axis=0))[0][[0, -1]]
                ymin, ymax = np.nonzero(np.any(mask, axis=1))[0][[0, -1]]
                bboxes[i] = [xmin, ymin, xmax - xmin + 1, ymax - ymin + 1]
            except IndexError:
                bboxes[i] = [0, 0, 0, 0]

    filename = os.path.basename(src_matfile_path)
    dst_file_path = pathlib.Path(src_matfile_path).parents[2] / f'BBoxes/{filename[:-4]}.npy'
    os.makedirs(pathlib.Path(dst_file_path).parent, exist_ok=True)
    np.save(dst_file_path, bboxes)


def extract_frames(src_video_path):
    """Save every 5th and 64th frame from a video as images."""
    print('Processing', src_video_path)
    video_name = pathlib.Path(src_video_path).stem
    dst_folder_path = pathlib.Path(src_video_path).parents[1] / 'Images' / video_name
    os.makedirs(dst_folder_path, exist_ok=True)

    with imageio.get_reader(src_video_path, 'ffmpeg') as reader:
        for i_frame, frame in enumerate(reader):
            if i_frame % 5 == 0 or i_frame % 64 == 0:
                dst_filename = f'frame_{i_frame:06d}.jpg'
                dst_path = os.path.join(dst_folder_path, dst_filename)
                if not os.path.exists(dst_path):
                    imageio.imwrite(dst_path, frame)


if __name__ == '__main__':
    main()
