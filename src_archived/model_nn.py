from keras.callbacks import EarlyStopping
from keras.layers.advanced_activations import PReLU
from keras.layers.core import Activation, Dense, Dropout
from keras.layers.normalization import BatchNormalization
from keras.models import Sequential, load_model
from keras.utils import np_utils
from sklearn.preprocessing import StandardScaler

from .model import AbsModel
from .util import Util

import os
import tensorflow as tf

# tensorflowの警告抑制
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '1'
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)


class ModelNN(AbsModel):
    """NNのモデルクラス

        Attributes:
            run_fold_name(str): 実行の名前とfoldの番号を組み合わせた名前
            params(dict): ハイパーパラメータ
            model(Model): 初期値はNoneで、train後に学習済みモデルを保持するのに使う
            scaler(Model): 初期値はNoneで、train後に学習済みscalerを保持するのに使う
    """

    def __init__(self, run_fold_name, params):
        super().__init__(run_fold_name, params)
        self.scaler = None

    def train(self, tr_x, tr_y, va_x=None, va_y=None):
        # データのセット・スケーリング
        validation = va_x is not None
        scaler = StandardScaler()
        scaler.fit(tr_x)
        tr_x = scaler.transform(tr_x)
        tr_y = np_utils.to_categorical(tr_y, num_classes=9)

        if validation:
            va_x = scaler.transform(va_x)
            va_y = np_utils.to_categorical(va_y, num_classes=9)

        # パラメータ
        nb_classes = 9
        layers = self.params['layers']
        dropout = self.params['dropout']
        units = self.params['units']
        nb_epoch = self.params['nb_epoch']
        patience = self.params['patience']

        # モデルの構築
        model = Sequential()
        model.add(Dense(units, input_shape=(tr_x.shape[1],)))
        model.add(PReLU())
        model.add(BatchNormalization())
        model.add(Dropout(dropout))

        for l in range(layers - 1):
            model.add(Dense(units))
            model.add(PReLU())
            model.add(BatchNormalization())
            model.add(Dropout(dropout))

        model.add(Dense(nb_classes))
        model.add(Activation('softmax'))
        model.compile(loss='categorical_crossentropy', optimizer='adam')

        if validation:
            early_stopping = EarlyStopping(monitor='val_loss',
                                           patience=patience,
                                           verbose=1,
                                           restore_best_weights=True
                                           )
            model.fit(tr_x,
                      tr_y,
                      epochs=nb_epoch,
                      batch_size=128,
                      verbose=2,
                      validation_data=(va_x, va_y),
                      callbacks=[early_stopping]
                      )
        else:
            model.fit(tr_x,
                      tr_y,
                      nb_epoch=nb_epoch,
                      batch_size=128,
                      verbose=2
                      )

        # モデル・スケーラーの保持
        self.model = model
        self.scaler = scaler

    def predict(self, te_x):
        te_x = self.scaler.transform(te_x)
        pred = self.model.predict_proba(te_x)
        return pred

    def save_model(self):
        model_path = os.path.join('../model_archived/model', f'{self.run_fold_name}.h5')
        scaler_path = os.path.join('../model_archived/model', f'{self.run_fold_name}-scaler.pkl')
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        self.model.save(model_path)
        Util.dump(self.scaler, scaler_path)

    def load_model(self):
        model_path = os.path.join('../model_archived/model', f'{self.run_fold_name}.h5')
        scaler_path = os.path.join('../model_archived/model', f'{self.run_fold_name}-scaler.pkl')
        self.model = load_model(model_path)
        self.scaler = Util.load(scaler_path)
