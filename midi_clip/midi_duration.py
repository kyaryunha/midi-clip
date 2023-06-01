import mido


def midi_duration(mid: mido.MidiFile) -> float:
    settings = dict(
        has_tempo_track=True,  # 첫 트랙이 tempo track 인지 확인
        tempo=500000,  # 현재 템포 저장 (파이썬 전역변수용..)
        elapsed_max=0.,  # 현재 누적 시간 중 가장 큰 값 저장 (미디의 끝)
        current_tempo_index=0,  # 현재 템포 인덱스 저장 (tempo track 일 떄만 사용됨)
        elapsed_seconds=0.,  # 현재 누적 시간 저장
    )

    def init_settings():
        settings["current_tempo_index"] = 0
        settings["elapsed_seconds"] = 0.

    #  has_tempo_track 이 True 인 경우에 쓰임
    tempo_changes = []

    for i, track in enumerate(mid.tracks):
        init_settings()
        # tempo track 이 먼저 나오는 구조인지 확인한다
        if i == 0:
            new_track = mido.MidiTrack()
            for msg in track:
                if msg.type == 'set_tempo':
                    settings["tempo_before_start"] = msg
                elif msg.type == 'end_of_track':
                    break
                if msg.type in ["note_on", "note_off"]:
                    settings["has_tempo_track"] = False
                    break
                settings["last_msg"] = msg

            if settings["has_tempo_track"] is True:
                if len(tempo_changes) == 0:
                    # note_on, note_off 가 없더라도, set_tempo 가 없으면 tempo track 이 아니다.
                    settings["has_tempo_track"] = False
            # 첫 트랙이 tempo track 이 아닌 경우 초기화
            init_settings()

        # tempo track 이 있을 경우 tempo track의 템포를 사용한다.
        if settings["has_tempo_track"] is True:
            settings["tempo"] = tempo_changes[0][1]

        # 미디 자르기
        for msg in track:
            # tempo track 이 존재할 경우 템포를 바꿔준다.
            if settings["has_tempo_track"] is True:
                if settings["current_tempo_index"] < len(tempo_changes) - 1 and \
                        settings["elapsed_seconds"] >= tempo_changes[settings["current_tempo_index"] + 1][0]:
                    settings["current_tempo_index"] += 1
                    settings["tempo"] = tempo_changes[settings["current_tempo_index"]][1]

            # tempo track 이 있더라도, 다른 트랙에 set_tempo가 있을 경우 일시적으로 해당 템포를 따라간다.
            if msg.type == 'set_tempo':
                settings["tempo"] = msg.tempo
            elif msg.type == 'end_of_track':
                break

            settings["elapsed_seconds"] += mido.tick2second(msg.time, mid.ticks_per_beat, settings["tempo"])
        settings["elapsed_max"] = max(settings["elapsed_max"], settings["elapsed_seconds"])
    return settings["elapsed_max"]