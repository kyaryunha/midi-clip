import mido


def midi_clip(mid: mido.MidiFile, start: float, end: float):
    output_mid = mido.MidiFile(ticks_per_beat=mid.ticks_per_beat)
    settings = dict(
        has_tempo_track=True,  # 첫 트랙이 tempo track 인지 확인
        tempo=500000,  # 현재 템포 저장 (파이썬 전역변수용..)
        current_tempo_index=0,  # 현재 템포 인덱스 저장 (tempo track 일 떄만 사용됨)
        elapsed_seconds=0.,  # 현재 누적 시간 저장
        end_of_track=False,  # 트랙의 끝이 나왔는지 확인
        last_note_time=0,  # 트랙의 끝일 때 마무리할 시간을 계산하는 목적
        is_start=False,  # 현재 재생 시간이 start 이상인지 (그러니까 저장해도 되는지)
        tick_delay=0,  # tick delay
        msg_before_start=None,  # start tick 이전에 가장 마지막에 나타난 msg
        last_msg=None,
        tempo_before_start=None,  # start tick 이전에 가장 마지막에 나타난 tempo track의 set_tempo msg
        time_signature_before_start=None,  # 노래가 시작하기 전에 마지막에 정의된 time_signature 가 있는지 확인한 후, 추가한다.
    )

    def init_settings():
        settings["current_tempo_index"] = 0
        settings["elapsed_seconds"] = 0.
        settings["end_of_track"] = False
        settings["last_note_time"] = 0
        settings["is_start"] = False
        settings["tick_delay"] = 0
        settings["msg_before_start"] = None
        settings["last_msg"] = None
        settings["tempo_before_start"] = None
        settings["time_signature_before_start"] = None

    #  has_tempo_track 이 True 인 경우에 쓰임
    tempo_changes = []

    for i, track in enumerate(mid.tracks):
        init_settings()
        control_changes_before_start = dict()  # 각 control number 별로 마지막에 나온 control_change 를 저장한다.
        # tempo track 이 먼저 나오는 구조인지 확인한다
        if i == 0:
            new_track = mido.MidiTrack()
            for msg in track:
                # is_start 체크 / 미디가 시작했을 때, start 이전에 나타난 msg가 있는지 확인하고, 있다면 해당 msg의 시간과의 차이를 계산한다.
                # 해당 before 메세지는 0에서 / 그 다음 메세지는 그 차이만큼의 시간을 가지도록 한다.
                # 그 차이가 딱 0인 경우에는 before 메세지는 추가하지 않고, 그 다음 메세지도 원래 자신의 시간만큼 가진다.
                # 근데 그 before 메세지가 set_tempo가 아닌 경우에는, 마지막에 나타는 set_tempo가 time=0으로 찍힌다.
                if settings["is_start"] is False and settings["elapsed_seconds"] >= start:
                    settings["is_start"] = True
                    settings["tick_delay"] = int(
                        mido.second2tick(settings["elapsed_seconds"] - start, mid.ticks_per_beat,
                                         settings["tempo"]))
                    # start-end 사이에 없더라도 마지막에 등장한 time_signature 를 저장할지?
                    if settings['time_signature_before_start'] is not None and settings["last_msg"] is not None and \
                            settings[
                                "last_msg"].type != 'time_signature':
                        settings['time_signature_before_start'].time = 0
                        new_track.append(settings['time_signature_before_start'])

                    # control changes 중 control 별로 가장 마지막에 등장했던 msg 들을 time=0으로 변경해서 저장함
                    except_control = []
                    if settings["last_msg"] is not None and settings["last_msg"].type == 'control_change':
                        except_control.append(settings["last_msg"].control)
                    for control_number in control_changes_before_start:
                        if control_number not in except_control:
                            control_change = control_changes_before_start[control_number].copy()
                            control_change.time = 0
                            new_track.append(control_change)
                    if settings["msg_before_start"] is not None:
                        if settings["msg_before_start"].type == 'note_on':
                            settings["msg_before_start"].time = 0
                            new_track.append(settings["msg_before_start"])
                    if settings["last_msg"] is not None:
                        if settings["last_msg"].type != 'set_tempo' and settings["tempo_before_start"] is not None:
                            settings["tempo_before_start"].time = 0
                            tempo_changes.append((0.0, settings["tempo_before_start"].tempo))
                            new_track.append(settings["tempo_before_start"])
                        settings["last_msg"].time = settings["tick_delay"]
                        settings["tick_delay"] = 0
                        new_track.append(settings["last_msg"])

                if msg.type == 'set_tempo':
                    if settings["is_start"] is True:
                        tempo_changes.append((settings["elapsed_seconds"], msg.tempo))
                    else:
                        settings["tempo_before_start"] = msg
                elif msg.type == 'control_change':
                    control_changes_before_start[msg.control] = msg
                elif msg.type == 'time_signature':
                    settings['time_signature_before_start'] = msg
                elif msg.type == 'end_of_track':
                    settings["end_of_track"] = True
                    break
                if msg.type in ["note_on", "note_off"]:
                    settings["has_tempo_track"] = False
                    break
                prev_elapsed_seconds = settings["elapsed_seconds"]
                settings["elapsed_seconds"] += mido.tick2second(msg.time, mid.ticks_per_beat, settings["tempo"])
                if settings["elapsed_seconds"] >= end:
                    settings["last_note_time"] = int(
                        mido.second2tick(end - prev_elapsed_seconds, mid.ticks_per_beat, settings["tempo"]))
                    break
                if settings["is_start"] is True:
                    if settings["tick_delay"] > 0:
                        msg.time += settings["tick_delay"]
                        settings["tick_delay"] = 0
                    new_track.append(msg)
                elif msg.type == "track_name":
                    # 곡이 시작되지 않았을 때 나온 track_name은 시간 0으로써, "가장 먼저 추가된다"
                    msg.time = 0
                    new_track.append(msg)
                    # 이런 경우 msg_before_start 나 last_msg 에 반영되지 않는다.
                    continue
                if settings["is_start"] is False:
                    settings["msg_before_start"] = settings["last_msg"]
                settings["last_msg"] = msg
            if settings["has_tempo_track"] is True:
                if settings["tempo_before_start"] is None:
                    # note_on, note_off 가 없더라도, set_tempo 가 없으면 tempo track 이 아니다.
                    settings["has_tempo_track"] = False
                else:
                    # 트랙이 시작보다 짧게 있더라도, tempo track 이 있다면, 마지막에 나온 tempo track을 시간 0으로 넣어 준다.
                    if settings["is_start"] is False:
                        settings["tempo_before_start"].time = 0
                        tempo_changes.append((0.0, settings["tempo_before_start"].tempo))
                        new_track.append(settings["tempo_before_start"])
                    new_track.append(mido.MetaMessage(type='end_of_track'))
                    output_mid.tracks.append(new_track)
                    continue
            # 첫 트랙이 tempo track 이 아닌 경우 초기화
            init_settings()
        # tempo track 이 있을 경우 tempo track의 템포를 사용한다.
        if settings["has_tempo_track"] is True:
            settings["tempo"] = tempo_changes[0][1]


        # on에 해당하는 off 를 생성하기 위해 (channel, note)의 msg 를 stack 형식으로 저장 (on 이면 push, off 면 pop)
        class Notes:
            def __init__(self):
                self.notes = dict()
                self._notes = dict()  # pop 하지 않는 기록용 배열

            def len(self, key):
                if key not in self.notes:
                    return None
                else:
                    return len(self.notes[key])

            def push(self, key, value, save=True):
                if key not in self.notes:
                    self.notes[key] = []
                self.notes[key].append(value)
                if save:
                    if key not in self._notes:
                        self._notes[key] = []
                    self._notes[key].append(value)

            def pop(self, key):
                if key not in self.notes:
                    raise IndexError('notes_pop failed / key not found: ', key)
                if len(self.notes[key]) == 0:
                    raise IndexError('notes_pop failed / index error: ', key)
                return self.notes[key].pop(0)

            def backup(self, key, idx):
                return self._notes[key][idx]
        # start 이전의 note 를 저장하고 이후 on에 해당하는 off는 추가하지 않는다.
        notes_before_start = Notes()  # 개수만 저장
        # start - end 사이의 note
        notes = Notes()

        new_track = mido.MidiTrack()
        # 미디 자르기
        for msg in track:
            # is_start 체크 / 미디가 시작했을 때, start 이전에 나타난 msg가 있는지 확인하고, 있다면 해당 msg의 시간과의 차이를 계산한다.
            # 해당 before 메세지는 0에서 / 그 다음 메세지는 그 차이만큼의 시간을 가지도록 한다.
            # 그 차이가 딱 0인 경우에는 before 메세지는 추가하지 않고, 그 다음 메세지도 원래 자신의 시간만큼 가진다.
            # 근데 그 before 메세지가 set_tempo가 아닌 경우에는, 마지막에 나타는 set_tempo가 time=0으로 찍힌다.
            # 근데 그 before 메세지가 note_off일 경우에는, 그 다음 메세지가 tick_delay 만큼의 시간을 추가로 가진다.
            if settings["is_start"] is False and settings["elapsed_seconds"] >= start:
                settings["is_start"] = True
                settings["tick_delay"] = int(mido.second2tick(settings["elapsed_seconds"] - start, mid.ticks_per_beat,
                                                              settings["tempo"]))
                # start-end 사이에 없더라도 마지막에 등장한 time_signature 를 저장할지?
                if settings['time_signature_before_start'] is not None and settings["last_msg"] is not None and \
                        settings["last_msg"].type != 'time_signature':
                    settings['time_signature_before_start'].time = 0
                    new_track.append(settings['time_signature_before_start'])

                # control changes 중 control 별로 가장 마지막에 등장했던 msg 들을 time=0으로 변경해서 저장함
                except_control = []
                if settings["last_msg"] is not None and settings["last_msg"].type == 'control_change':
                    except_control.append(settings["last_msg"].control)

                for control_number in control_changes_before_start:
                    if control_number not in except_control:
                        control_change = control_changes_before_start[control_number].copy()
                        control_change.time = 0
                        new_track.append(control_change)
                last_msg_note_on_key = None
                if settings["last_msg"] is not None:
                    if settings["last_msg"].type == 'note_on':
                        last_msg_note_on_key = (settings["last_msg"].channel, settings["last_msg"].note)
                    elif settings["last_msg"].type == 'note_off':
                        note_on = notes_before_start.backup((settings["last_msg"].channel, settings["last_msg"].note), -1)
                        notes_before_start.push((settings["last_msg"].channel, settings["last_msg"].note), note_on, False)
                for (channel, note) in notes_before_start.notes:
                    for idx, _msg in enumerate(notes_before_start.notes[(channel, note)]):
                        if (channel, note) == last_msg_note_on_key and (idx == len(notes_before_start.notes[(channel, note)]) - 1):
                            pass
                        note_on = _msg.copy()
                        note_on.time = 0
                        new_track.append(note_on)
                        notes.push((channel, note), note_on)

                if settings["last_msg"] is not None:
                    if settings["last_msg"].type != 'set_tempo' and settings["tempo_before_start"] is not None:
                        settings["tempo_before_start"].time = 0
                        tempo_changes.append((0.0, settings["tempo_before_start"].tempo))
                        new_track.append(settings["tempo_before_start"])

                    settings["last_msg"].time = settings["tick_delay"]
                    settings["tick_delay"] = 0
                    if settings["last_msg"].type == 'note_on':
                        notes.push((settings["last_msg"].channel, settings["last_msg"].note), settings["last_msg"])
                    elif settings["last_msg"].type == 'note_off':
                        notes.pop((settings["last_msg"].channel, settings["last_msg"].note))
                    new_track.append(settings["last_msg"])

            # tempo track 이 존재할 경우 템포를 바꿔준다.
            if settings["has_tempo_track"] is True:
                if settings["current_tempo_index"] < len(tempo_changes) - 1 and \
                        settings["elapsed_seconds"] >= tempo_changes[settings["current_tempo_index"] + 1][0]:
                    settings["current_tempo_index"] += 1
                    settings["tempo"] = tempo_changes[settings["current_tempo_index"]][1]

            # tempo track 이 있더라도, 다른 트랙에 set_tempo가 있을 경우 일시적으로 해당 템포를 따라간다.
            if msg.type == 'set_tempo':
                settings["tempo"] = msg.tempo
                if settings["is_start"] is False:
                    settings["tempo_before_start"] = msg
            elif msg.type == 'control_change':
                control_changes_before_start[msg.control] = msg
            elif msg.type == 'time_signature':
                settings['time_signature_before_start'] = msg
            elif msg.type == 'end_of_track':
                settings["end_of_track"] = True
                break

            prev_elapsed_seconds = settings["elapsed_seconds"]
            settings["elapsed_seconds"] += mido.tick2second(msg.time, mid.ticks_per_beat, settings["tempo"])
            if settings["elapsed_seconds"] >= end:
                settings["last_note_time"] = int(
                    mido.second2tick(end - prev_elapsed_seconds, mid.ticks_per_beat, settings["tempo"]))
                break
            if msg.type in ["note_on", "note_off"]:
                if settings["is_start"] is True:
                    if settings["tick_delay"] > 0:
                        msg.time += settings["tick_delay"]
                        settings["tick_delay"] = 0
                    new_track.append(msg)
                    if msg.type == 'note_on':
                        notes.push((msg.channel, msg.note), msg)
                    elif msg.type == 'note_off':
                        notes.pop((msg.channel, msg.note))
                else:
                    # 자르는 구간이 시작되지 않은 note 일 경우, 해당 노트를 저장한다.
                    if msg.type == 'note_on':
                        notes_before_start.push((msg.channel, msg.note), msg)
                    elif msg.type == 'note_off':
                        notes_before_start.pop((msg.channel, msg.note))
            elif settings["is_start"] is True:
                if settings["tick_delay"] > 0:
                    msg.time += settings["tick_delay"]
                    settings["tick_delay"] = 0
                new_track.append(msg)
            elif msg.type == "track_name":
                # 곡이 시작되지 않았을 때 나온 track_name은 시간 0으로써, "가장 먼저 추가된다"
                msg.time = 0
                new_track.append(msg)
                # 이런 경우 msg_before_start 나 last_msg 에 반영되지 않는다.
                continue
            if settings["is_start"] is False:
                settings["msg_before_start"] = settings["last_msg"]
            settings["last_msg"] = msg

        # tempo track 이 아닌데, 시작하지도 않았거나, 이미 끝나버린 경우.
        if settings["is_start"] is False or len(new_track) == 1:
            continue
        if settings["end_of_track"] is False:
            # note_on 닫아주기
            for (channel, note) in notes.notes:
                for _ in range(0, len(notes.notes[(channel, note)])):
                    new_track.append(
                        mido.Message(type="note_off", channel=channel, note=note, time=settings["last_note_time"]))
                    # 두 번째 부터는 무조건 0초
                    settings["last_note_time"] = 0
        new_track.append(mido.MetaMessage('end_of_track', time=settings["last_note_time"]))
        output_mid.tracks.append(new_track)
    return output_mid
