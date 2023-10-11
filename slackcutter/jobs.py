import datetime
import json
import os
import statistics
import subprocess
from itertools import combinations
from pathlib import Path
from typing import Union

import cv2
import joblib
import numpy as np
import pandas as pd
from pydub import AudioSegment
from slackcutter import config


class Jobs:
    @staticmethod
    def extractImages(pathIn: Path, pathOut: Path) -> dict:
        # возвращает dict rgb-раскладку пикселей с подписью фрейма
        pathIn_str = str(pathIn)
        pathOut_str = str(pathOut)

        count = 0

        vidcap = cv2.VideoCapture(pathIn_str)

        # нужно пережать само видео в 240р, не кадры

        success, image = vidcap.read()
        full_dict = {}

        success = True
        while success:
            try:
                vidcap.set(cv2.CAP_PROP_POS_MSEC, (count * 1000))  # added this line
                success, image = vidcap.read()
                if config.extractImages_output_choice is True:
                    print("Read a new frame: ", success)
                # image = cv2.resize(image,(pixel_quantity,1),fx=0,fy=0, interpolation = cv2.INTER_CUBIC)

                if config.extractImages_need_save is True:
                    cv2.imwrite(
                        pathOut_str + "\\frame%d.jpg" % count,
                        image,
                    )  # save frame as JPEG file

                # https://habr.com/ru/post/519454/ анализ цветов пикселей
                if config.extractImages_output_choice is True:
                    print(
                        "Высота:" + str(image.shape[0]),
                        "Ширина:" + str(image.shape[1]),
                    )

                # (b, g, r) = image[719, 1279] # пиксель в точке 0,0
                # автоматически в json

                # temp_dict = {}
                temp_list = []
                for i in range(0, config.extractImages_pixel_quantity):
                    (b, g, r) = image[0, i]

                    if config.extractImages_output_choice is True:
                        print("Красный: {}, Зелёный: {}, Синий: {}".format(r, g, b))

                    # temp_dict[i] = [int(r), int(g), int(b)]
                    temp_list.append([int(r), int(g), int(b)])

                full_dict[count] = temp_list

                count += 1  # every 1 second

            except Exception as e:
                print(e)

        return full_dict

    @staticmethod
    def audio_info_extractor_job7(
        path: Path,
        low_percentage_audio: int,
        high_percentage_audio: int,
    ) -> dict:
        # This will open and read the audio file with pydub.  Replace the file path with
        # your own file.
        begin_time = datetime.datetime.now()

        audio_file = AudioSegment.from_file(path)

        # Set up a list for us to dump PCM samples into, and create a 'data' variable
        # so we don't need to type audio_file._data again
        data = audio_file._data
        pcm16_signed_integers = []

        # This loop decodes the bytestring into PCM samples.
        # The bytestring is a stream of little-endian encoded signed integers.
        # This basically just cuts each two-byte sample out of the bytestring, converts
        # it to an integer, and appends it to the list of samples.
        for sample_index in range(len(data) // 2):
            sample = int.from_bytes(
                data[sample_index * 2 : sample_index * 2 + 2],
                "little",
                signed=True,
            )
            pcm16_signed_integers.append(sample)

        print(len(pcm16_signed_integers) / audio_file.duration_seconds)
        step = int(len(pcm16_signed_integers) / audio_file.duration_seconds)
        chunks = [
            pcm16_signed_integers[x : x + step]
            for x in range(0, len(pcm16_signed_integers), step)
        ]

        print(datetime.datetime.now() - begin_time)

        sound_seconds_dict = {}

        for i in range(0, len(chunks)):
            temp_list = []
            temp_list.append(int(sum(chunks[i]) / len(chunks[i])))
            temp_list.append(int(statistics.median(chunks[i])))
            temp_list.append(min(chunks[i]))
            temp_list.append(max(chunks[i]))

            # порядок: среднее, медиана, мин, макс
            sound_seconds_dict[i] = temp_list

        sound_df = pd.DataFrame.from_dict(sound_seconds_dict)
        sound_df

        # внедрение поиска ударов по секундам

        a_median = np.array(list(sound_df.T[1]))
        p_25_median = np.percentile(a_median, low_percentage_audio)  # 25
        p_75_median = np.percentile(a_median, high_percentage_audio)  # 75

        a_max = np.array(list(sound_df.T[3]))
        p_25_max = np.percentile(a_max, low_percentage_audio)  # noqa: F841
        p_75_max = np.percentile(
            a_max,
            high_percentage_audio,
        )  # можно динамично искать лучший перцентиль ай гесс

        for i in sound_seconds_dict:
            if (
                sound_seconds_dict[i][1] > 0 and sound_seconds_dict[i][1] > p_75_median
            ) or (
                sound_seconds_dict[i][1] < 0 and sound_seconds_dict[i][1] > p_25_median
            ):
                sound_seconds_dict[i].append(1)
            else:
                sound_seconds_dict[i].append(0)

            if sound_seconds_dict[i][3] > p_75_max:
                sound_seconds_dict[i].append(1)
            else:
                sound_seconds_dict[i].append(0)

        return sound_seconds_dict

    @staticmethod
    def pixel_delta_analizer_job7(
        max_frame_quantity: int,
        delta_type: str,
        low_percentage: int,
        high_percentage: int,
    ) -> pd.DataFrame:
        # Opening JSON file
        map_dest = Path(config.temp_folder, config.map_folder)

        with open(map_dest.joinpath("frame_pixels.json").as_posix()) as json_file:
            data = json.load(json_file)

        deltas_df = pd.DataFrame.from_dict(data)

        with open(
            map_dest.joinpath("frame_audio_samples.json").as_posix(),
        ) as json_file:
            data_audio = json.load(json_file)

        # data_audio = sound_seconds_dict

        audio_df = pd.DataFrame.from_dict(data_audio)

        # audio_df = audio_df.drop(columns=["0"])

        fin_deltas_df = deltas_df.append(audio_df)

        fin_deltas_df = fin_deltas_df.reset_index()
        del fin_deltas_df["index"]
        fin_deltas_df = fin_deltas_df.T

        fin_deltas_df = fin_deltas_df.rename(
            columns={
                6: "среднее_аудио",
                7: "медиана",
                8: "мин",
                9: "макс",
                10: "удар_по_медиане",
                11: "удар_по_максу",
            },
        )
        fin_deltas_df

        frame_delta_restrictions = {}

        for i in range(0, 6):
            a_0 = np.array(list(fin_deltas_df[i]))
            p_25_0 = np.percentile(a_0, low_percentage)
            p_75_0 = np.percentile(a_0, high_percentage)
            # print(p_25_0, p_75_0)
            frame_delta_restrictions[i] = [p_25_0, p_75_0]

        frame_delta_restrictions

        # подсчет по дельте ргб
        change_frame_list = []  # type: ignore # noqa: F841
        # по колву пикселей надо смотреть

        return fin_deltas_df

    @staticmethod
    def scenes_split_on_median(
        fin_deltas_df: pd.DataFrame,
        median_hit_modificator: Union[int, float],
    ) -> list[int]:
        # нарезка сцен по медиане
        z = 0

        count_0 = 0
        count_1 = 0

        frames_map = [0]

        for i in list(fin_deltas_df["удар_по_медиане"]):
            if i == 1:
                count_1 += 1
            else:
                count_0 += 1

            try:
                if count_1 / count_0 < median_hit_modificator:
                    frames_map.append(z)
                    count_1 = 0
                    count_0 = 0
            except:  # noqa: E722
                pass

            z += 1

        return frames_map

    @staticmethod
    def scene_mapping(
        frames_map: list[int],
        min_crop_interval: int,
        max_crop_interval: int,
    ) -> pd.DataFrame:
        # мапинг текущей сцены с прошлой
        xxx = []
        prev = 0

        for i in frames_map:
            xxx.append(i - prev)
            prev = i

        df_cropframes = pd.DataFrame.from_dict({0: frames_map, 1: xxx})

        df_cropframes = df_cropframes.rename(columns={0: "end_sec", 1: "len_sec"})
        df_cropframes["start_sec"] = df_cropframes["end_sec"] - df_cropframes["len_sec"]

        print("стартовая длина df_cropframes:", len(df_cropframes))

        # старт_сек равны индексам
        df_cropframes = df_cropframes.loc[
            (df_cropframes["len_sec"] >= min_crop_interval)
            & (df_cropframes["len_sec"] < max_crop_interval)
        ].reset_index()
        del df_cropframes["index"]

        df_cropframes = df_cropframes.loc[
            (df_cropframes["len_sec"] >= min_crop_interval)
            & (df_cropframes["len_sec"] < max_crop_interval)
        ].reset_index()
        del df_cropframes["index"]

        # старт_сек равны индексам
        return df_cropframes

    @staticmethod
    def create_all_single_scenes(
        df_cropframes: pd.DataFrame,
        fin_deltas_df: pd.DataFrame,
    ) -> pd.DataFrame:
        # создание полного набора единичных сцен

        fin_pairs_df = pd.DataFrame()

        list_full_info = []
        list_first_frame_rgb = []
        list_last_frame_rgb = []
        list_first_frame_timestamp = []
        list_last_frame_timestamp = []
        list_len_sec = []

        for ind in range(0, len(df_cropframes)):

            len_sec = df_cropframes["len_sec"][ind]
            list_len_sec.append(len_sec)

            curr_start = df_cropframes["start_sec"][ind]
            curr_end = df_cropframes["end_sec"][ind]

            frame_1_rgb = []  # type: ignore # noqa: F841
            frame_m1_rgb = []  # type: ignore # noqa: F841
            list_mean_audio = []  # type: ignore # noqa: F841
            list_median = []  # type: ignore # noqa: F841
            list_min = []  # type: ignore # noqa: F841
            list_max = []  # type: ignore # noqa: F841
            list_median_hit = []  # type: ignore # noqa: F841
            list_max_hit = []  # type: ignore # noqa: F841

            tmp_crop_df = fin_deltas_df[curr_start : curr_end + 1].reset_index()

            tmp_crop_df[-1 : len(tmp_crop_df)]

            full_info = tmp_crop_df.to_dict("index")
            first_frame_rgb = tmp_crop_df.values.tolist()[0][1:7]
            last_frame_rgb = tmp_crop_df.values.tolist()[-1][1:7]
            first_frame_timestamp = tmp_crop_df.values.tolist()[0][0]
            last_frame_timestamp = tmp_crop_df.values.tolist()[-1][0]

            list_full_info.append(full_info)
            list_first_frame_rgb.append(first_frame_rgb)
            list_last_frame_rgb.append(last_frame_rgb)
            list_first_frame_timestamp.append(first_frame_timestamp)
            list_last_frame_timestamp.append(last_frame_timestamp)

        fin_pairs_df["full_info"] = list_full_info
        fin_pairs_df["first_frame_rgb"] = list_first_frame_rgb
        fin_pairs_df["last_frame_rgb"] = list_last_frame_rgb
        fin_pairs_df["first_frame_timestamp"] = list_first_frame_timestamp
        fin_pairs_df["last_frame_timestamp"] = list_last_frame_timestamp
        fin_pairs_df["len_sec"] = list_len_sec

        return fin_pairs_df

    @staticmethod
    def create_all_scenes_combinations(fin_pairs_df: pd.DataFrame) -> pd.DataFrame:
        # создание всех комбинаций пар сцен
        # так был получен датасет с основной инфой по парам, теперь нужно их все перекомбинировать и найти дельны

        L = range(0, len(fin_pairs_df) - 1)
        all_combinations_list = [list(comb) for comb in combinations(L, 2)]

        print("длина all_combinations_list:", len(all_combinations_list))

        # ужасный подход, потом во время поддержки кода надо будет оптимизировать

        pairs_for_deltas_df = pd.DataFrame()

        for_pairs_dict: dict = {
            "full_info_0": [],
            "first_frame_rgb_0": [],
            "last_frame_rgb_0": [],
            "first_frame_timestamp_0": [],
            "last_frame_timestamp_0": [],
            "len_sec_0": [],
            "full_info_1": [],
            "first_frame_rgb_1": [],
            "last_frame_rgb_1": [],
            "first_frame_timestamp_1": [],
            "last_frame_timestamp_1": [],
            "len_sec_1": [],
        }

        for_names_list = [
            "full_info",
            "first_frame_rgb",
            "last_frame_rgb",
            "first_frame_timestamp",
            "last_frame_timestamp",
            "len_sec",
        ]

        # тут оч жесткая алгоритмическая сложность накрутилась, потом пофиксить
        for comb_id in all_combinations_list:
            first_id = comb_id[0]  # first
            second_id = comb_id[1]  # second

            for pair_name_id in for_pairs_dict:
                for targat_name in for_names_list:
                    if targat_name in pair_name_id:
                        if "_0" in pair_name_id:
                            for_pairs_dict[pair_name_id].append(
                                fin_pairs_df[targat_name][first_id],
                            )
                        elif "_1" in pair_name_id:
                            for_pairs_dict[pair_name_id].append(
                                fin_pairs_df[targat_name][second_id],
                            )
                        else:
                            print("wtf")

        for fin_names in for_pairs_dict:
            pairs_for_deltas_df[fin_names] = for_pairs_dict[fin_names]

        # и вот до сюда оптимизировать

        return pairs_for_deltas_df

    @staticmethod
    def get_frame_deltas_lists(
        data: pd.Series,
        prev: pd.Series,
        max_frame_quantity: int,
        pairs_for_deltas_df: pd.DataFrame,
        delta_type: str,
    ) -> list:

        temp_list = []  # type: ignore # noqa: F841

        full_frame_deltas = []

        for pair_index in range(0, len(pairs_for_deltas_df)):
            big_temp_list = []

            for frame_id in range(0, max_frame_quantity):
                temp = []

                for rgb_index in range(0, 3):  # итерации по ргб
                    temp.append(
                        data[pair_index][frame_id][rgb_index]
                        - prev[pair_index][frame_id][rgb_index],
                    )

                if delta_type == "full":
                    big_temp_list.append(temp)
                elif delta_type == "mean":
                    big_temp_list.append(sum(temp) / 3)  # type: ignore
                else:
                    assert delta_type == "mean" or delta_type == "full", "wtf"

            full_frame_deltas.append(big_temp_list)

        return full_frame_deltas

    @staticmethod
    def create_frame_deltas_pairs(
        pairs_for_deltas_df: pd.DataFrame,
        max_frame_quantity: int,
        delta_type: str,
    ) -> pd.DataFrame:
        # создание пар для дельт кадров

        data = pairs_for_deltas_df["last_frame_rgb_0"]
        prev = pairs_for_deltas_df["first_frame_rgb_1"]

        full_frame_deltas = Jobs.get_frame_deltas_lists(
            data,
            prev,
            max_frame_quantity,
            pairs_for_deltas_df,
            delta_type,
        )

        pairs_for_deltas_df["pair_deltas"] = full_frame_deltas

        all_med_hits = []
        column_name = "full_info_0"

        for frame_index in range(0, len(pairs_for_deltas_df)):
            med_hits = []

            for fr_row in pairs_for_deltas_df[column_name][frame_index]:
                med_hits.append(
                    pairs_for_deltas_df[column_name][frame_index][fr_row][
                        "удар_по_медиане"
                    ],
                )

            mean_med_hits = sum(med_hits) / len(med_hits)

            all_med_hits.append(mean_med_hits)

        pairs_for_deltas_df["median_mean_hits_0"] = all_med_hits

        return pairs_for_deltas_df

    @staticmethod
    def add_median_hit_statistics(pairs_for_deltas_df: pd.DataFrame) -> pd.DataFrame:
        # добавление статистики хитов по медиане
        all_med_hits = []
        column_name = "full_info_1"

        # алгоритмическая сложность
        for frame_index in range(0, len(pairs_for_deltas_df)):
            med_hits = []

            for fr_row in pairs_for_deltas_df[column_name][frame_index]:
                med_hits.append(
                    pairs_for_deltas_df[column_name][frame_index][fr_row][
                        "удар_по_медиане"
                    ],
                )

            mean_med_hits = sum(med_hits) / len(med_hits)

            all_med_hits.append(mean_med_hits)

        pairs_for_deltas_df["median_mean_hits_1"] = all_med_hits

        pairs_for_deltas_df["median_mean_hits_mean_0_1"] = (
            pairs_for_deltas_df["median_mean_hits_0"]
            + pairs_for_deltas_df["median_mean_hits_1"]
        ) / 2

        return pairs_for_deltas_df

    @staticmethod
    def calculate_rgb_frame_deltas(
        pairs_for_deltas_df: pd.DataFrame,
        max_frame_quantity: int,
        delta_type: str,
    ) -> tuple[pd.DataFrame, dict]:
        # подсчет дельт по ргб для кадров

        comparison_df = pairs_for_deltas_df[["last_frame_rgb_0", "first_frame_rgb_1"]]
        print("длина comparison_df:", len(comparison_df))

        dict_data_new = {}
        count = 0
        data = comparison_df["first_frame_rgb_1"]
        prev = comparison_df["last_frame_rgb_0"]

        # алгоритмическая сложность
        for i in range(0, len(comparison_df["last_frame_rgb_0"])):
            big_temp_list = []
            for frame_id in range(0, max_frame_quantity):  # итерации по кадрам

                temp = []
                for rgb_index in range(0, 3):  # итерации по ргб
                    temp.append(
                        data[i][frame_id][rgb_index] - prev[i][frame_id][rgb_index],
                    )

                if delta_type == "full":
                    big_temp_list.append(temp)
                elif delta_type == "mean":
                    big_temp_list.append(sum(temp) / 3)  # type: ignore
                else:
                    assert delta_type == "mean" or delta_type == "full", "wtf"

                dict_data_new[i] = big_temp_list

            count += 1

        return comparison_df, dict_data_new

    @staticmethod
    def markup_frame_pixels(
        dict_data_new: dict,
        max_frame_quantity: int,
    ) -> tuple[list, dict]:
        # быстрый скрипт разметки, юзаем счетчик, итерируемся по списку, счетчик также
        # юзаем по маршрутизации по словарю в зависимости от локального индекса в списке
        list_data_new: list = []
        dict_razmetka: dict = {}

        for i in range(0, max_frame_quantity):
            dict_razmetka[i] = []

        for step in dict_data_new:
            z = 0
            for i in dict_data_new[step]:
                dict_razmetka[z].append(i)
                z += 1

            list_data_new.append(dict_data_new[step])

        return list_data_new, dict_razmetka

    @staticmethod
    def predict_and_make_dataset(
        trained_model: Path,
        dict_razmetka: dict,
        max_frame_quantity: int,
        comparison_df: pd.DataFrame,
    ) -> list:

        rfc = joblib.load(trained_model)

        for i in dict_razmetka:
            comparison_df[i] = dict_razmetka[i]

        predict_df = comparison_df[list(range(0, max_frame_quantity))]

        propaility_list = []
        print("длина predict_df: ", len(predict_df))
        for i in rfc.predict_proba(predict_df):
            propaility_list.append(i[1])

        return propaility_list

    @staticmethod
    def rank_modelled_scenes(
        pairs_for_deltas_df: pd.DataFrame,
        propaility_list: list,
        model_threshold: Union[int, float],
    ) -> pd.DataFrame:
        # ранжирование смоделированных сцен

        pairs_for_deltas_df["propaility"] = propaility_list

        pairs_for_deltas_df["scene_id_0"] = (
            pairs_for_deltas_df["first_frame_timestamp_0"]
            + "_"
            + pairs_for_deltas_df["last_frame_timestamp_0"]
        )
        pairs_for_deltas_df["scene_id_1"] = (
            pairs_for_deltas_df["first_frame_timestamp_1"]
            + "_"
            + pairs_for_deltas_df["last_frame_timestamp_1"]
        )

        pairs_for_deltas_df["scene_id_0"].unique

        print(len(pairs_for_deltas_df))
        pairs_for_deltas_df = pairs_for_deltas_df.loc[
            pairs_for_deltas_df["propaility"] > model_threshold
        ]
        print(len(pairs_for_deltas_df))

        # код выборки сцены

        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # ult_temp_df.loc[~ult_temp_df.isin({'scene_id_1': no_repeats_list})['scene_id_1']]
        # вот эту кононструкцию выписать и в рамочку

        df_chosen_scenes = pd.DataFrame()
        testlist = []  # type: ignore # noqa: F841

        no_repeats_list: list = []

        # надо доп проверку списком чтобы не было при выборе уже использованных вторых кадров
        # вот тут основное ранжирование
        scene_id = "scene_id_0"
        for scene_index in list(pairs_for_deltas_df[scene_id].unique()):

            temp_df = pairs_for_deltas_df.loc[
                pairs_for_deltas_df[scene_id] == scene_index
            ].sort_values(by=["median_mean_hits_mean_0_1"], ascending=False)
            temp_df = temp_df.reset_index()
            temp_df["first_frame_timestamp_1"] = temp_df[
                "first_frame_timestamp_1"
            ].astype(int)
            temp_df["last_frame_timestamp_1"] = temp_df[
                "last_frame_timestamp_1"
            ].astype(int)
            temp_df["first_frame_timestamp_0"] = temp_df[
                "first_frame_timestamp_0"
            ].astype(int)
            temp_df["last_frame_timestamp_0"] = temp_df[
                "last_frame_timestamp_0"
            ].astype(int)
            temp_df["timestamp_check"] = (
                temp_df["last_frame_timestamp_0"] - temp_df["first_frame_timestamp_1"]
            )

            # проверка но репитс
            ult_temp_df = (
                temp_df.loc[
                    (
                        temp_df["median_mean_hits_mean_0_1"]
                        == temp_df["median_mean_hits_mean_0_1"][0]
                    )
                    & (temp_df["timestamp_check"] != -1)
                ]
                .sort_values(by=["first_frame_timestamp_1"], ascending=True)
                .reset_index(drop=True)
            )

            # самая глючная часть
            ult_temp_df = ult_temp_df.loc[
                ult_temp_df['scene_id_1'].apply(lambda x: x not in no_repeats_list)
                ].reset_index(drop = True)[0:1]
            df_chosen_scenes = df_chosen_scenes.append(ult_temp_df)
            try:
                no_repeats_list.append(
                    ult_temp_df['scene_id_1'][0]
                )
            except:  # noqa: E722
                pass

            # алгоритмическая сложность
            if len(ult_temp_df) == 0:
                schet_temp = 1
                stopper = 0
                while stopper == 0:
                    try:
                        ult_temp_df = (
                            temp_df.loc[
                                (
                                    temp_df["median_mean_hits_mean_0_1"]
                                    == temp_df["median_mean_hits_mean_0_1"][schet_temp]
                                )
                                & (temp_df["timestamp_check"] != -1)
                            ]
                            .sort_values(by=["first_frame_timestamp_1"], ascending=True)
                            .reset_index(drop=True)
                        )
                        ult_temp_df = ult_temp_df.loc[
                                ult_temp_df['scene_id_1'].apply(lambda x: x not in no_repeats_list)
                            ].reset_index(drop = True)[0:1]
                        df_chosen_scenes = df_chosen_scenes.append(ult_temp_df)
                        no_repeats_list.append(
                            ult_temp_df['scene_id_1'][0]
                        )
                        if len(ult_temp_df) != 0:
                            stopper += 1
                    except:  # noqa: E722
                        if schet_temp > len(
                            pairs_for_deltas_df["median_mean_hits_mean_0_1"].unique(),
                        ):
                            stopper += 1

                        schet_temp += 1

            no_repeats_list = list(set(no_repeats_list))

        del df_chosen_scenes["index"]
        df_chosen_scenes = df_chosen_scenes.reset_index()
        del df_chosen_scenes["index"]

        target_df = df_chosen_scenes.sort_values(by=["propaility"], ascending=False)[
            [
                "last_frame_timestamp_0",
                "first_frame_timestamp_0",
                "last_frame_timestamp_1",
                "first_frame_timestamp_1",
            ]
        ].reset_index(drop=True)

        return target_df

    @staticmethod
    def prepare_secs_crop_list(target_df: pd.DataFrame) -> list:
        # разметка по формату
        fin_list = []
        for i in range(0, len(target_df)):
            temp_list = []
            temp_list.append(target_df["first_frame_timestamp_0"][i])
            temp_list.append(target_df["last_frame_timestamp_0"][i])

            fin_list.append(temp_list)

            temp_list = []
            temp_list.append(target_df["first_frame_timestamp_1"][i])
            temp_list.append(target_df["last_frame_timestamp_1"][i])

            fin_list.append(temp_list)

        return fin_list

    @staticmethod
    def crop_vid(
        secs_crop_list: list,
        vid_path: Path,
        path_save: Path,
        sound_check: bool,
        max_seconds: int,
    ) -> list:
        # режет видео, кладет в папку, кладет в папку дблокнот, возвращает список названий видео
        # формат кроплиста [[0,1],[9,11]]
        max_seconds = max_seconds  # 120 secs for example
        vid_names = []
        z = 0
        tempor_seconds = 0
        for i in secs_crop_list:
            if tempor_seconds < max_seconds:
                start_sec_str = str(datetime.timedelta(seconds=int(i[0])))
                end_sec_str = str(datetime.timedelta(seconds=int(i[1])))

                output_path = Path(path_save, f"output_{z}_{vid_path.name}")
                if sound_check is True:
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-ss",
                            start_sec_str,
                            "-to",
                            end_sec_str,
                            "-i",
                            vid_path,
                            "-c",
                            "copy",
                            output_path,
                        ],
                    )
                else:
                    subprocess.run(
                        [
                            "ffmpeg",
                            "-ss",
                            start_sec_str,
                            "-to",
                            end_sec_str,
                            "-i",
                            vid_path,
                            "-c",
                            "copy",
                            "-an",
                            output_path,
                        ],
                    )

                vid_names.append(Path(f"output_{str(z)}_{vid_path.name}"))
                z += 1

            tempor_seconds += i[1] - i[0]  # добавили

        # пишем названия видео в блокнот и сейвим
        path_to_txt = Path(path_save, config.txt_list_name)
        with open(path_to_txt, "w") as fp:
            for item in vid_names:
                fp.write("file '%s'\n" % item)
            print("Done")

        return vid_names

    @staticmethod
    def connect_vids_and_delete(
        input_list_dest: Path,
        output_dest: Path,
        sound_check: bool,
        file_names: list,
    ) -> None:
        # file_names = fin_names # итоговый список имен
        # start_path = path_save # путь старта
        # save_path = path_save # путь сохранения
        # txt_list_name = 'vid_names.txt' # название текстового файла с разметкой

        if sound_check is True:
            subprocess.run(
                [
                    "ffmpeg",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    input_list_dest,
                    "-c",
                    "copy",
                    output_dest,
                ],
            )
        else:
            subprocess.run(
                [
                    "ffmpeg",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    input_list_dest,
                    "-c",
                    "copy",
                    "-an",
                    output_dest,
                ],
            )

        for file in file_names:
            os.remove(Path(output_dest.parent, file))

        print("connecting done")
