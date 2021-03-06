"""
/home/algomorph/Factory/calib_video_opencv/audiosync/convert.py.
Created on Feb 9, 2016.
@author: Gregory Kramida
@licence: Apache v2

Copyright 2016 Gregory Kramida

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from calib.camera import Camera
import os.path

def __sync_ranges(frame_durations, frame_rates, frame_ranges, frame_offsets):
    """
    Synchronize frame_ranges, i.e. make sure that frame_ranges match after the offset is applied
    """
    post_offset_bounds = (0,min(frame_durations))
    for ix_range in range(0,len(frame_ranges)):
        frame_range = frame_ranges[ix_range]
        frame_offset = frame_offsets[ix_range]
        post_offset_bounds = (max(post_offset_bounds[0], frame_range[0]-frame_offset), 
                              min(post_offset_bounds[1],frame_range[1]-frame_offset))
    frame_ranges = []
    time_ranges = []
    for ix_range in range(0,len(frame_offsets)):
        frame_offset = frame_offsets[ix_range]
        fps = frame_rates[ix_range]
        frame_range = (frame_offset + post_offset_bounds[0], frame_offset + post_offset_bounds[1])
        frame_ranges.append(frame_range)
        time_ranges.append((frame_range[0]/fps, frame_range[1]/fps))
    return frame_ranges, time_ranges


def find_offset_range(video_filenames, folder, offset, cut_off_end = 2.0):
    """
    Find frame & time ranges where to clip provided video files based on specified offset & cut-off.
    """
    source_videos = []
    frame_durations = []
    frame_offsets = []
    ranges = []
    frame_rates = []
    ix_vid = 0
    
    for file_name in video_filenames:
        camera = Camera(os.path.join(folder, file_name))
        frame_durations.append(camera.frame_count)
        source_videos.append(camera)
        frame_offset = int(camera.fps * offset[ix_vid])
        frame_offsets.append(frame_offset)
        trim_frames = int(camera.fps * cut_off_end)
        frame_rates.append(camera.fps)
        ranges.append((frame_offset, camera.frame_count - trim_frames))
        del camera # explicitly release video file
        ix_vid += 1
        
    return __sync_ranges(frame_durations, frame_rates, ranges, frame_offsets)


def find_calibration_conversion_range(video_filenames, folder, offset, board_dims, 
                                      seek_time_interval=1.0, cut_off_end=20.0, verbose=True):
    """
    Find ranges where to clip the videos for calibration, i.e. the first frame where the calibration
    board appears and the last, as constrained by provided offset between the videos, the
    specified cut-off at the end (in seconds), and the seek interval (in seconds).
    @type video_filenames: list[str]
    @param video_filenames: names of the video files
    @type folder: str
    @param folder: path of the folder where the video files reside
    @type board_dims: tuple[int]
    @param board_dims: dimensions of the calibration board
    @type offset: list[int]
    @param offset: time offset, in frames, from the first video
    @type seek_time_interval: float
    @param seek_time_interval: time interval in seconds
    @type cut_off_end: float
    @param cut_off_end: how much (minimum) to cut off the end of both videos (seconds)
    @type verbose: bool
    @param verbose: whether to print progress & results to standard output
    @rtype: list[tuple[int]]
    @return proper ranges to clip the videos for calibration.
    """
    source_videos = []
    for file_name in video_filenames:
        camera = Camera(os.path.join(folder, file_name))
        source_videos.append(camera)
        
    ix_vid = 0
    ranges = []
    frame_offsets = []
    frame_durations =[]
    frame_rates = []
    for camera in source_videos:
        frame_durations.append(camera.frame_count)
        frame_offset = int(camera.fps * offset[camera.index])
        frame_offsets.append(frame_offset)
        frame_rates.append(camera.fps)
        
        i_frame = frame_offset
        camera.scroll_to_frame(i_frame)
        camera.read_next_frame()
        skip_interval = int(seek_time_interval * camera.fps)
        
        # find the first frame with corners past the offset mark
        cont_cap = True
        if verbose:
            print("Seeking first frame of {0:s} usable for calibration...".format(camera.name))
        while cont_cap:
            found_corners = camera.try_approximate_corners(board_dims)
            i_frame += skip_interval
            camera.scroll_to_frame(i_frame)
            if i_frame > (camera.frame_count-1):
                camera.more_frames_remain = False
                break
            camera.read_next_frame()
            cont_cap = camera.more_frames_remain and not found_corners
            if verbose:
                print('.',end="",flush=True)
        
        if not camera.more_frames_remain:
            raise ValueError("Could not find a frame in the video containing the checkerboard!")
        
        start_frame = i_frame
        
        if verbose:
            print("\nFound at frame {0:d} ({1:.3f} s).".format(start_frame, start_frame / camera.fps))

        # find the last frame with corners
        i_frame = camera.frame_count-1 - int(camera.fps * cut_off_end)
        camera.scroll_to_frame(i_frame)
        camera.read_next_frame()
        found_corners = False
        if verbose:
            print("Seeking last usable frame of {0:s}...".format(camera.name))
        while not found_corners:
            found_corners = camera.try_approximate_corners(board_dims)
            i_frame -= skip_interval
            camera.scroll_to_frame(i_frame)
            camera.read_next_frame()
            if verbose:
                print('.', end="", flush=True)
        # add one for exclusive right bound
        end_frame = i_frame + 1
        
        if verbose:
            print("\nFound at frame {0:d} ({1:.3f} s).".format(end_frame, end_frame / camera.fps))
            
        del camera # explicitly release video file
        
        ranges.append((start_frame, end_frame))
        ix_vid += 1

    return __sync_ranges(frame_durations, frame_rates, ranges, frame_offsets)
