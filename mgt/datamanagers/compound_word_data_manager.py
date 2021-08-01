from pretty_midi import pretty_midi

from mgt.datamanagers.compound_word.compound_word_mapper import CompoundWordMapper
from mgt.datamanagers.data_manager import DataManager, DataSet
from mgt.datamanagers.midi_wrapper import MidiWrapper, MidiToolkitWrapper
from mgt.datamanagers.remi import util
from mgt.datamanagers.remi.dictionary_generator import DictionaryGenerator


class CompoundWordDataManager(DataManager):

    def __init__(self, transposition_steps=None, map_tracks_to_instruments=None):
        if map_tracks_to_instruments is None:
            map_tracks_to_instruments = {}
        if transposition_steps is None:
            transposition_steps = [0]
        self.transposition_steps = transposition_steps
        self.map_tracks_to_instruments = map_tracks_to_instruments
        self.dictionary = DictionaryGenerator.create_dictionary()
        self.compound_word_mapper = CompoundWordMapper(self.dictionary)

    def prepare_data(self, midi_paths) -> DataSet:
        training_data = []
        for path in midi_paths:
            for transposition_step in self.transposition_steps:
                try:
                    data = util.extract_words(path,
                                              transposition_steps=transposition_step,
                                              map_tracks_to_instruments=self.map_tracks_to_instruments,
                                              use_chords=False)

                    compound_words = self.compound_word_mapper.map_to_compound(data, self.dictionary)
                    compound_data = self.compound_word_mapper.map_compound_words_to_data(compound_words)

                    training_data.append(compound_data)
                except Exception as e:
                    print(e)

        return DataSet(training_data, self.dictionary)

    def to_midi(self, data) -> MidiWrapper:
        remi = self.compound_word_mapper.map_to_remi(data)
        return MidiToolkitWrapper(util.to_midi(remi, self.dictionary))
