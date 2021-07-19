from pretty_midi import pretty_midi

from mgt.datamanagers.data_manager import DataManager, DataSet
from mgt.datamanagers.midi_wrapper import MidiWrapper, MidiToolkitWrapper
from mgt.datamanagers.remi import util
from mgt.datamanagers.remi.dictionary_generator import DictionaryGenerator


class RemiDataManager(DataManager):

    def __init__(self, use_chords=True, transposition_steps=None, map_tracks_to_instruments=None, allow_empty_bars=False):
        if map_tracks_to_instruments is None:
            map_tracks_to_instruments = {}
        if transposition_steps is None:
            transposition_steps = [0]
        self.use_chords = use_chords
        self.transposition_steps = transposition_steps
        self.map_tracks_to_instruments = map_tracks_to_instruments
        self.dictionary = DictionaryGenerator.create_dictionary()
        self.allow_empty_bars = allow_empty_bars

    def prepare_data(self, midi_paths) -> DataSet:
        training_data = []
        for path in midi_paths:
            for transposition_step in self.transposition_steps:
                try:
                    data = util.extract_data(path,
                                             transposition_steps=transposition_step,
                                             map_tracks_to_instruments=self.map_tracks_to_instruments,
                                             dictionary=self.dictionary,
                                             use_chords=self.use_chords,
                                             allow_empty_bars=self.allow_empty_bars)
                    training_data.append(data)
                except Exception as e:
                    print(e)

        return DataSet(training_data, self.dictionary)

    def to_midi(self, data) -> MidiWrapper:
        return MidiToolkitWrapper(util.to_midi(data, self.dictionary))
