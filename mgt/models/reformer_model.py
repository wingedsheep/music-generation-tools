from datetime import time

import numpy as np
import torch
import time

from reformer_pytorch import ReformerLM
from reformer_pytorch.generative_tools import TrainingWrapper
from x_transformers import AutoregressiveWrapper

from mgt.datamanagers.data_manager import Dictionary


def create_chunks(iterable, chunk_size=1):
    array_length = len(iterable)
    for ndx in range(0, array_length, chunk_size):
        yield iterable[ndx:min(ndx + chunk_size, array_length)]


def create_sequences(training_data, max_sequence_length, padding_character=0):
    sequences = []
    for song in training_data:
        padded_song = list(np.repeat([padding_character], max_sequence_length)) + song
        for i in range(len(padded_song) - max_sequence_length):
            sequence = padded_song[i: i + max_sequence_length]
            sequences.append(sequence)
    return sequences


class ReformerModel(object):

    def __init__(self,
                 dictionary: Dictionary,
                 max_sequence_length=2048,
                 learning_rate=1e-3,
                 full_attn_thres=512,
                 lsh_dropout=0.1,
                 depth=6,
                 dim=512,
                 heads=6
                 ):
        self.dictionary = dictionary
        self.max_sequence_length = max_sequence_length
        self.learning_rate = learning_rate
        self.full_attn_thres = full_attn_thres
        self.lsh_dropout = lsh_dropout
        self.depth = depth
        self.dim = dim
        self.heads = heads
        self.model = self.create_model()
        self.optimizer = self.create_optimizer()

    def train(self, x_train, epochs, batch_size=8, stop_loss=0.1, batches_per_epoch=100, report_per_x_batches=5):
        self.model.train()
        start_time = time.time()
        sequences = create_sequences(x_train, self.max_sequence_length)
        for epoch in range(epochs):
            print(f"Training epoch {epoch + 1}.")

            indices = np.random.randint(0, len(sequences), batch_size * batches_per_epoch)
            batches = list(create_chunks(np.array(sequences)[indices], chunk_size=batch_size))

            epoch_losses = []
            batch_losses = []
            nr_of_batches_processed = 0
            for batch in batches:
                # when training, set return_loss equal to True
                loss = self.model(torch.tensor(batch).long().cuda(), return_loss=True)
                loss.backward()

                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                self.optimizer.step()
                self.optimizer.zero_grad()

                nr_of_batches_processed += 1

                loss_item = loss.item()

                batch_losses.append(loss_item)
                epoch_losses.append(loss_item)

                if nr_of_batches_processed % report_per_x_batches == 0:
                    print(f"Processed {nr_of_batches_processed} / {len(batches)} with loss {np.mean(batch_losses)}.")
                    batch_losses = []

            epoch_loss = np.mean(epoch_losses)
            if epoch_loss <= stop_loss:
                print(f"Loss of {epoch_loss} was lower than stop loss of {stop_loss}. Stopping training.")
                return

            running_time = (time.time() - start_time)
            print(f"Loss after epoch {epoch + 1} is {epoch_loss}. Running time: {running_time}")

    def generate(self, output_length=100):
        self.model.eval()
        initial = torch.tensor([[0]]).long().cuda()  # assume 0 is start token

        sample = self.model.generate(initial, output_length, temperature=1., filter_thres=0.9)
        return sample.cpu().detach().numpy()[0]

    def create_model(self):
        model = ReformerLM(
            num_tokens=self.dictionary.size() + 1,
            dim=self.dim,
            depth=self.depth,
            max_seq_len=self.max_sequence_length,
            lsh_dropout=self.lsh_dropout,
            causal=True,
            full_attn_thres=self.full_attn_thres,
            heads=self.heads
        )

        # 0 is used for padding and no loss to be calculated on it
        training_wrapper = AutoregressiveWrapper(model, ignore_index=0, pad_value=0).cuda()
        return training_wrapper

    def create_optimizer(self):
        return torch.optim.Adam(self.model.parameters(), lr=self.learning_rate)

    def save_model(self, path):
        checkpoint = {'state_dict': self.model.state_dict(), 'optimizer': self.optimizer.state_dict()}
        if path.endswith("_sd_opt.pth"):
            torch.save(checkpoint, path + "_sd_opt.pth")
        else:
            torch.save(checkpoint, path + "_sd_opt.pth")

    def load_model(self, path):
        if path.endswith("_sd_opt.pth"):
            torch.load(path)
        else:
            torch.load(path + "_sd_opt.pth")
        self.model.eval()
