import datetime
import json
import os
import subprocess
from pathlib import Path
from shutil import rmtree
from typing import Union

import pandas as pd
from slackcutter import config
from slackcutter.jobs import Jobs


class SlackCutter:
    """Class for handling user input and making clip."""

    __max_frame_quantity = 6
    __delta_type = "mean"

    def __init__(
        self,
        source_name: str,
        trained_model_name: str,
        output_name: str = "output.mp4",
        max_seconds_length: int = 150,
        model_threshold: float = 0.2,
        sound_check: bool = False,
        noice_threshold: list = [10, 90],
        audio_threshold: list = [25, 75],
        median_hit_modificator: float = 1.5,
        crop_interval: list = [1, 5],
    ):
        """
        Constructor to handle user input.

        :param source_name: Name of the source video file (ex: example.mp4).
        :param trained_model_name: Name of the trained model (ex: RanFor_Action Sports.joblib).
        :param output_name: Name of the final clip (ex: output.mp4).
        :param max_seconds_length: Clip's lenght in seconds (ex: 150).
        :param model_threshold: Magic. (ex: 0.2)
        :param sound_check: Clip's sound presence. True - with sound, False - without (ex: True).
        :param noice_threshold: Magic. (ex: [10, 90])
        :param audio_threshold: Magic. (ex: [25, 75])
        :param median_hit_modificator: Magic. (ex: 1.5)
        :param crop_interval: Magic. (ex: [1, 5])
        """
        self.__output_dir = Path(config.output_folder)
        self.__map_dest = Path(config.temp_folder, config.map_folder)
        self.__temp_media_dest = Path(config.temp_folder, config.temp_media_folder)
        self.__temp_images_dest = Path(config.temp_folder, config.temp_images_folder)

        self.source_dest = source_name  # type: ignore
        self.output_name = output_name  # type: ignore
        self.trained_model = trained_model_name  # type: ignore
        self.max_clip_seconds_lenght = max_seconds_length
        self.model_threshold = model_threshold
        self.sound_check = sound_check
        self.noice_threshold = noice_threshold
        self.audio_threshold = audio_threshold
        self.median_hit_modificator = median_hit_modificator
        self.crop_interval = crop_interval

    def recreate_folders(self) -> None:
        """Creates main used folders by application and deletes existing."""

        temp_dir = Path(config.temp_folder)

        if temp_dir.is_dir():
            rmtree(temp_dir)

        if self.__output_dir.is_dir():
            rmtree(self.__output_dir)

        self.__output_dir.mkdir(parents=True, exist_ok=True)
        self.__map_dest.mkdir(parents=True, exist_ok=True)
        self.__temp_media_dest.mkdir(parents=True, exist_ok=True)
        self.__temp_images_dest.mkdir(parents=True, exist_ok=True)

    def generate_temp_media(self) -> None:
        """Generates application's temp media."""

        temp_video_dest = Path(self.__temp_media_dest, config.temp_video)
        temp_audio_dest = Path(self.__temp_media_dest, config.temp_audio)

        try:
            os.remove(temp_video_dest)
            os.remove(temp_audio_dest)
        except:  # noqa: E722
            pass

        subprocess.run(
            ["ffmpeg", "-i", self.source_dest, "-vf", "scale=6:720", temp_video_dest],
        )
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                temp_video_dest,
                "-q:a",
                "9",
                "-map",
                "a",
                "-ar",
                "8000",
                "-ac",
                "1",
                temp_audio_dest,
            ],
        )

    def make_clip(self) -> None:
        """Makes clip with user settings and outputs it in output folder."""

        self.recreate_folders()
        self.generate_temp_media()

        frame_pixels = self.__generate_frame_pixels()  # noqa: F841
        sound_seconds_dict = self.__generate_frame_audio_samples()  # noqa: F841
        fin_deltas_df = self.__generate_fin_deltas_df()

        frames_map = Jobs.scenes_split_on_median(
            fin_deltas_df,
            self.__median_hit_modificator,
        )
        print("длина frames_map:", len(frames_map))

        df_cropframes = Jobs.scene_mapping(frames_map, *self.crop_interval)
        print("длина df_cropframes:", len(df_cropframes))

        fin_pairs_df = Jobs.create_all_single_scenes(df_cropframes, fin_deltas_df)
        pairs_for_deltas_df = Jobs.create_all_scenes_combinations(fin_pairs_df)
        pairs_for_deltas_df = Jobs.create_frame_deltas_pairs(
            pairs_for_deltas_df,
            self.max_frame_quantity,
            self.delta_type,
        )
        pairs_for_deltas_df = Jobs.add_median_hit_statistics(pairs_for_deltas_df)
        comparison_df, dict_data_new = Jobs.calculate_rgb_frame_deltas(
            pairs_for_deltas_df,
            self.max_frame_quantity,
            self.delta_type,
        )
        list_data_new, dict_razmetka = Jobs.markup_frame_pixels(
            dict_data_new,
            self.max_frame_quantity,
        )
        propaility_list = Jobs.predict_and_make_dataset(
            self.trained_model,
            dict_razmetka,
            self.max_frame_quantity,
            comparison_df,
        )

        path_map = Path(self.__map_dest, config.temp_map_json)
        target_df = Jobs.rank_modelled_scenes(
            pairs_for_deltas_df,
            propaility_list,
            self.__model_threshold,
        )
        target_df.to_json(path_map, orient="records", lines=True)

        target_df = pd.read_json(path_map, orient="records", lines=True)
        secs_crop_list = Jobs.prepare_secs_crop_list(target_df)
        fin_names = Jobs.crop_vid(
            secs_crop_list,
            self.source_dest,
            self.__output_dir,
            self.sound_check,
            self.max_clip_seconds_lenght,
        )

        input_list_dest = Path(self.__output_dir, config.txt_list_name)
        Jobs.connect_vids_and_delete(
            input_list_dest,
            self.__output_dest,
            self.sound_check,
            fin_names,
        )

    def __generate_frame_pixels(self) -> dict:
        # job 1

        begin_time = datetime.datetime.now()

        path_to_video = Path(self.__temp_media_dest, config.temp_video)
        path_to_images = self.__temp_images_dest
        frame_pixels = Jobs.extractImages(path_to_video, path_to_images)

        print("длина frame_pixels:", len(frame_pixels))

        print(datetime.datetime.now() - begin_time)

        # первый слой - номер кадра, второй слой - номер пикселя
        with open(self.__map_dest.joinpath("frame_pixels.json").as_posix(), "w") as fp:
            json.dump(frame_pixels, fp)

        return frame_pixels

    def __generate_frame_audio_samples(self) -> dict:
        # job 3

        path_to_audio = Path(self.__temp_media_dest, config.temp_audio)
        sound_seconds_dict = Jobs.audio_info_extractor_job7(
            path_to_audio, *self.audio_threshold
        )

        print("длина sound_seconds_dict:", len(sound_seconds_dict))

        with open(
            self.__map_dest.joinpath("frame_audio_samples.json").as_posix(),
            "w",
        ) as fp:
            json.dump(sound_seconds_dict, fp)

        return sound_seconds_dict

    def __generate_fin_deltas_df(self) -> pd.DataFrame:
        # job 4

        fin_deltas_df = Jobs.pixel_delta_analizer_job7(
            self.max_frame_quantity, self.delta_type, *self.noice_threshold
        )

        # system job
        vid_json_path = Path(self.__map_dest, f"{self.source_dest.name}.json")
        with open(vid_json_path, "w") as fp:
            json.dump(fin_deltas_df.to_json(), fp)

        os.remove(Path(self.__temp_media_dest, config.temp_video))
        os.remove(Path(self.__temp_media_dest, config.temp_audio))

        print("длина fin_deltas_df:", len(fin_deltas_df))
        print(
            "распределение ударов по медиане: ",
            dict(fin_deltas_df["удар_по_медиане"].value_counts()),
        )

        return fin_deltas_df

    @property
    def source_dest(self) -> Path:
        """Return your initial video file path."""

        return self.__source_dest

    @source_dest.setter
    def source_dest(self, source_name: str) -> None:
        self.__source_dest = Path(source_name)
        if not self.__source_dest.is_file():
            raise Exception(f"No such file: {self.__source_dest}")

    @property
    def trained_model(self) -> Path:
        """Return your trained model path."""

        return self.__trained_model_dest

    @trained_model.setter
    def trained_model(self, trained_model_name: str) -> None:
        self.__trained_model_dest = Path(
            config.trained_models_folder,
            trained_model_name,
        )
        self.__trained_model_dest.parent.mkdir(parents=True, exist_ok=True)
        if not self.__trained_model_dest.is_file():
            raise Exception(f"No such trained model: {self.__trained_model_dest}")

    @property
    def max_clip_seconds_lenght(self) -> int:
        """Return max clip lenght set by user."""

        return self.__max_seconds

    @max_clip_seconds_lenght.setter
    def max_clip_seconds_lenght(self, max_seconds_length: int) -> None:
        """
        Sets clip's lenght in seconds. Also checks if desired length not exceeds source file length.

        :param max_seconds_length: Clip's lenght in seconds.
        """

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                self.source_dest,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        try:
            if max_seconds_length < int(float(result.stdout)):
                self.__max_seconds = max_seconds_length
            else:
                raise Exception("Desired output length exceeds video limits.")
        except ValueError:
            raise Exception(result.stdout.decode("utf-8"))

    @property
    def output_name(self) -> Path:
        """Return output file path."""

        return self.__output_dest

    @output_name.setter
    def output_name(self, output_name: str) -> None:
        self.__output_dest = Path(self.__output_dir, output_name)

    @property
    def sound_check(self) -> bool:
        """Return sound_check bool property."""

        return self.__sound_check

    @sound_check.setter
    def sound_check(self, boolean: bool) -> None:
        if not isinstance(boolean, bool):
            raise Exception("sound_check must be boolean value.")
        self.__sound_check = boolean

    @property
    def noice_threshold(self) -> list[int]:
        """Return noice threshold in a min-max list."""

        return [self.__low_percentage, self.__high_percentage]

    @noice_threshold.setter
    def noice_threshold(self, minmax: list[int]) -> None:
        if len(minmax) != 2:
            raise Exception("noice_threshold must be a list with minmax values.")
        if minmax[1] < minmax[0]:
            raise Exception("First value must be minimal. Example: [10, 90]")
        self.__low_percentage = minmax[0]
        self.__high_percentage = minmax[1]

    @property
    def audio_threshold(self) -> list[int]:
        """Return audio threshold in a min-max list."""

        return [self.__low_percentage_audio, self.__high_percentage_audio]

    @audio_threshold.setter
    def audio_threshold(self, minmax: list[int]) -> None:
        if len(minmax) != 2:
            raise Exception("audio_threshold must be a list with minmax values.")
        if minmax[1] < minmax[0]:
            raise Exception("First value must be minimal. Example: [25, 75]")
        self.__low_percentage_audio = minmax[0]
        self.__high_percentage_audio = minmax[1]

    @property
    def crop_interval(self) -> list[int]:
        """Return crop interval in a min-max list."""

        return [self.__min_crop_interval, self.__max_crop_interval]

    @crop_interval.setter
    def crop_interval(self, minmax: list[int]) -> None:
        if len(minmax) != 2:
            raise Exception("crop_interval must be a list with minmax values.")
        if minmax[1] < minmax[0]:
            raise Exception("First value must be minimal. Example: [1, 5]")
        self.__min_crop_interval = minmax[0]
        self.__max_crop_interval = minmax[1]

    @property
    def model_threshold(self) -> Union[int, float]:
        """Return model threshold."""

        return self.__model_threshold

    @model_threshold.setter
    def model_threshold(self, value: Union[int, float]) -> None:
        if not isinstance(value, int) and not isinstance(value, float):
            raise Exception("model_threshold must be either int or float.")
        self.__model_threshold = value

    @property
    def median_hit_modificator(self) -> Union[int, float]:
        """Return median hit modifier."""

        return self.__median_hit_modificator

    @median_hit_modificator.setter
    def median_hit_modificator(self, value: Union[int, float]) -> None:
        if not isinstance(value, int) and not isinstance(value, float):
            raise Exception("median_hit_modificator must be either int or float.")
        self.__median_hit_modificator = value

    @property
    def max_frame_quantity(self) -> int:
        return self.__max_frame_quantity

    @max_frame_quantity.setter
    def max_frame_quantity(self, value: int) -> None:
        if not isinstance(value, int):
            raise Exception("max_frame_quantity must be int.")
        self.__max_frame_quantity = value

    @property
    def delta_type(self) -> str:
        return self.__delta_type

    def switch_delta_type(self) -> str:
        """Switches current delta_type propery. It might be either "mean" or "full"."""

        self.__delta_type = "mean" if self.__delta_type == "full" else "full"
        return self.__delta_type
