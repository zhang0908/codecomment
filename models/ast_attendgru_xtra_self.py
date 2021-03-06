from keras.models import Model
from keras.layers import Input, Maximum, Dense, Embedding, Reshape, GRU, merge, LSTM, Dropout, BatchNormalization, Activation, concatenate, multiply, MaxPooling1D, Conv1D, Flatten, Bidirectional, CuDNNGRU, RepeatVector, Permute, TimeDistributed, dot
from keras.backend import tile, repeat, repeat_elements
from keras.optimizers import RMSprop, Adamax
import keras
import keras.utils
import tensorflow as tf

# I write this guide with much thanks to:
# https://wanasit.github.io/attention-based-sequence-to-sequence-in-keras.html
# https://arxiv.org/abs/1508.04025

class AstAttentionGRUModelXtraSelf:
    def __init__(self, config):
        self.datvocabsize = config['datvocabsize']
        self.comvocabsize = config['comvocabsize']
        self.smlvocabsize = config['smlvocabsize']
        self.datlen = config['datlen']
        self.comlen = config['comlen']
        self.smllen = config['smllen']

        
        self.embdims = 100
        self.smldims = 10
        self.recdims = 128
        self.num_input = 3
    def create_model(self):
        
        dat_input = Input(shape=(self.datlen,))
        com_input = Input(shape=(self.comlen,))
        sml_input = Input(shape=(self.smllen,))
        
        ee = Embedding(output_dim=self.embdims, input_dim=self.datvocabsize, mask_zero=False)(dat_input)
        se = Embedding(output_dim=self.smldims, input_dim=self.smlvocabsize, mask_zero=False)(sml_input)

        #se_emb = Conv1D(10, 3)(se)
        #se_emb = MaxPooling1D()(se_emb)
        #se_enc = Flatten()
        #seout = se_enc(se_emb)
        se_enc = CuDNNGRU(self.recdims, return_state=True, return_sequences=True)
        #se_enc = GRU(self.recdims, return_state=True, return_sequences=True, activation='tanh', unroll=True)
        seout, state_sml = se_enc(se)

        enc = CuDNNGRU(self.recdims, return_state=True, return_sequences=True)
        #enc = GRU(self.recdims, return_state=True, return_sequences=True, activation='tanh', unroll=True)
        encout, state_h = enc(ee)#, initial_state=state_sml)
        
        
        de = Embedding(output_dim=self.embdims, input_dim=self.comvocabsize, mask_zero=False)(com_input)
        #dec = GRU(self.recdims, return_sequences=True, activation='tanh', unroll=True)
        dec_sml = CuDNNGRU(self.recdims, return_sequences=True)
        dec_dat = CuDNNGRU(self.recdims, return_sequences=True)
        #dec_sml = GRU(self.recdims, return_sequences=True, activation='tanh', unroll=True)
        #dec_dat = GRU(self.recdims, return_sequences=True, activation='tanh', unroll=True)
        decout_sml = dec_sml(de, initial_state=state_sml)
        decout_dat = dec_dat(de, initial_state=state_h)
        
        attn = dot([decout_dat, encout], axes=[2, 2])
        attn = Activation('softmax')(attn)

        ast_attn = dot([decout_sml, seout], axes=[2, 2])
        ast_attn = Activation('softmax')(ast_attn)

        context = dot([attn, encout], axes=[2, 1])
        ast_context = dot([ast_attn, seout], axes=[2, 1])

        #seout = RepeatVector(self.comlen)(seout)

        context = concatenate([context, decout_sml, decout_dat, ast_context])


        out = TimeDistributed(Dense(self.recdims, activation="relu"))(context)

        out = Flatten()(out)
        #out = concatenate([seout, out])
        #out = Dense(2048, activation='relu')(out)
        out = Dense(self.comvocabsize, activation="softmax")(out)
        
        model = Model(inputs=[dat_input, com_input, sml_input], outputs=out)

        
        model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
        return self.num_input, model
