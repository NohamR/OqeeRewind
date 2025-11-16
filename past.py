"""Script for testing and analyzing past Oqee streams and manifests."""
import datetime

from dotenv import load_dotenv

from utils.stream import fetch_drm_keys
from utils.times import (
    convert_date_to_sec,
    convert_sec_to_ticks
)

TIMESCALE = 90000
DURATION = 288000
load_dotenv()


if __name__ == '__main__':
    # mpd_content = get_manifest('201') # 201: france 2
    # manifest_info = parse_mpd_manifest(mpd_content)

    # organized_info = organize_by_content_type(manifest_info)
    # with open('manifest_organized.json', 'w') as f:
    #     json.dump(organized_info, f, indent=4)

    drm_kid = "0dfa399a-425d-3095-0255-f357e2407edf"
    drm_kid = drm_kid.replace("-", "")
    print('kid: ', drm_kid)
    print(fetch_drm_keys(drm_kid))


    # dt = datetime.datetime.strptime("2023-12-14 23:02:14", "%Y-%m-%d %H:%M:%S")
    dt = datetime.datetime.strptime("2025-11-13 23:02:14", "%Y-%m-%d %H:%M:%S")
    tick = int(convert_sec_to_ticks(convert_date_to_sec(dt), TIMESCALE))
    # print(tick)

    # # 1280x720, 3000
    # track_id = "0_1_390"
    # base = 153232896078968

    # # 1920x1080, 14800
    # track_id = "0_1_3525"
    # # not found

    # # 1920x1080, 4800
    video_track_id = "0_1_3524"
    video_base1 = 153232896150968

    # audio fra_main
    audio_track_id = "0_1_384"
    audio_base2 = 153232896097804


    # asyncio.run(bruteforce(track_id, tick))


    # # https://catalogue.ina.fr/doc/TV-RADIO/TV_8165000.001/Bordeaux_%2Bchampagne%2B_%2Bquand%2Bles%2Bescrocs%2Bs_attaquent%2Ba%2Bnos%2Bbouteilles%2B_
    # # 14/12/2023 23:02:22 - 24:12:22
    # start = "2023-12-14 23:02:22"
    # start_tick1, start_rep1 = find_nearest_tick_by_hour(
    #     video_base1, start, TIMESCALE, DURATION
    # )
    # start_tick2, start_rep2 = find_nearest_tick_by_hour(
    #     audio_base2, start, TIMESCALE, DURATION
    # )

    # end = "2023-12-15 00:12:22"
    # end_tick1, end_rep1 = find_nearest_tick_by_hour(
    #     video_base1, end, TIMESCALE, DURATION
    # )
    # end_tick2, end_rep2 = find_nearest_tick_by_hour(
    #     audio_base2, end, TIMESCALE, DURATION
    # )

    # rep_nb = end_rep1 - start_rep1

    # diff_start = start_tick2 - start_tick1
    # diff_start_sec = convert_ticks_to_sec(diff_start, TIMESCALE)
    # print('diff_start_sec: ', diff_start_sec)
    # print(f"Total segments to fetch: {rep_nb}")
    
    # # Download the segments
    # asyncio.run(save_segments(track_id, start_tick, rep_nb, duration))


    # cat $(ls -v *.m4s) > merged.m4s

    # get_init(track_id)
    # kid = get_kid(track_id)
    # print("KID:", kid)
    # key = fetch_drm_keys(kid)
    # print("KEY:", key)

    # mp4ff-decrypt -init init.mp4 -key f31708f7237632849c591202e3043417
    # merged.m4s merged_dec.m4s
    # command_decrypt = (
    #     f"mp4ff-decrypt -init segments/segments_{track_id}/init.mp4 "
    #     f"-key {key} segments/segments_{track_id}/merged.m4s merged_dec.m4s"
    # )
    # print("Decrypt command:", command_decrypt)

    # ffmpeg -i "concat:init.mp4|merged_dec.m4s" -c copy output.mp4
    # command_ffmpeg = (
    #     f'ffmpeg -i "concat:segments/segments_{track_id}/init.mp4|'
    #     f'merged_dec.m4s" -c copy output.mp4'
    # )
    # print("FFmpeg command:", command_ffmpeg)

    # command_merge = (
    #     f"ffmpeg -i video.mp4 -itsoffset {diff_start_sec} "
    #     f"-i audio.mp4 -c copy -map 0:v -map 1:a output.mp4"
    # )
    # print("Merge command:", command_merge)





    # TF1 research (manifest id : 612)
    # 2023-06-10 is the latest available date for TF1 0_1_382 and 0_1_381

    # dt = datetime.datetime.strptime("2023-06-10 08:00:00", "%Y-%m-%d %H:%M:%S")
    # # dt = datetime.datetime.strptime("2023-09-01 08:00:00", "%Y-%m-%d %H:%M:%S")
    # tick = int(convert_sec_to_ticks(convert_date_to_sec(dt), TIMESCALE))

    # # 1280x720, 3000
    # track_id = "0_1_382"
    # asyncio.run(bruteforce(track_id, tick))
