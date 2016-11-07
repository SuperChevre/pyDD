# -*- coding: utf-8 -*-
"""
@author: Ardalan MEHRANI <ardalan77400@gmail.com>
@brief:
"""

import os
import json
import time
import tempfile
import numpy as np
from sklearn.datasets import dump_svmlight_file
from pydd.utils import os_utils
from pydd.utils import time_utils
from pydd.utils.dd_utils import AbstractDDCalls, to_array


class genericMLP(AbstractDDCalls):
    def __init__(self, host='localhost',
                 port=8080,
                 sname='',
                 mllib='caffe',
                 description='',
                 repository='',
                 templates='../templates/caffe',
                 connector='svm',
                 nclasses=None,
                 ntargets=None,
                 gpu=False,
                 gpuid=0,
                 template='mlp',
                 layers=[50],
                 activation='relu',
                 dropout=0.5,
                 regression=False,
                 finetuning=False,
                 db=True):

        self.host = host
        self.port = port
        self.sname = sname
        self.mllib = mllib
        self.n_pred = 0
        self.n_fit = 0
        self.calls = []
        self.answers = []
        self.model = {'templates': templates, 'repository': repository}
        self.description = description
        self.service_parameters_mllib = {'nclasses': nclasses, 'ntargets': ntargets,
                                         'gpu': gpu, 'gpuid': gpuid,
                                         'template': template, 'layers': layers,
                                         'activation': activation,
                                         'dropout': dropout, 'regression': regression,
                                         'finetuning': finetuning, 'db': db}
        self.service_parameters_input = {'connector': connector}
        self.service_parameters_output = {}
        super(genericMLP, self).__init__(self.host, self.port)

        if self.sname == '':
            self.sname = "pyDD_MLP_{}".format(time_utils.fulltimestamp())
            self.description = self.sname
        else:
            self.delete_service(self.sname, "mem")

        tmp_dir = tempfile.mkdtemp()
        self.data_folder = "{}/data".format(tmp_dir)
        if self.model['repository'] == '':
            self.model['repository'] = "{}/model".format(tmp_dir)
        os_utils._create_dirs([self.model['repository'], self.data_folder])

        json_dump = self.create_service(self.sname, self.model, self.description, self.mllib,
                                        self.service_parameters_input, self.service_parameters_mllib,
                                        self.service_parameters_output)
        self.answers.append(json_dump)

        with open("{}/model.json".format(self.model['repository'])) as f:
            self.calls = [json.loads(line, encoding='utf-8') for line in f]

    def __repr__(self):
        return self.__class__.__name__

    def fit(self, filepaths, iterations=100, test_interval=None, base_lr=0.1,
            solver_type='SGD', batch_size=128, metrics=['mcll', 'accp'], class_weights=None):

        self.filepaths = [filepaths] if type(filepaths) is not list else filepaths

        # df: True otherwise core dump when training on svm data
        self.train_parameters_input = {'db': True},
        self.train_parameters_output = {"measure": metrics},
        self.train_parameters_mllib = {
            'gpu': self.service_parameters_mllib['gpu'],
            'solver': {'iterations': iterations,
                       'test_interval': test_interval,
                       'base_lr': base_lr,
                       'solver_type': solver_type},
            'net': {'batch_size': batch_size},
            'class_weights': class_weights if class_weights else [1.] * self.service_parameters_mllib['nclasses']
        }

        if self.n_fit > 0:
            self.delete_service(self.sname, "mem")
            if 'template' in self.service_parameters_mllib:
                self.service_parameters_mllib.pop('template')

            self.create_service(self.sname, self.model, self.description, self.mllib,
                                self.service_parameters_input,
                                self.service_parameters_mllib,
                                self.service_parameters_output)

        json_dump = self.post_train(self.sname,
                                    self.filepaths,
                                    self.train_parameters_input,
                                    self.train_parameters_mllib,
                                    self.train_parameters_output, async=True)
        time.sleep(1)
        self.answers.append(json_dump)
        with open("{}/model.json".format(self.model['repository'])) as f:
            self.calls = [json.loads(line, encoding='utf-8') for line in f]

        self.n_fit += 1

        train_status = ''
        while True:
            train_status = self.get_train(self.sname, job=1, timeout=2)
            if train_status['head']['status'] == 'running':
                print(train_status['body']['measure'])
            else:
                print(train_status)
                break

    def predict_proba(self, svm_filepath):

        nclasses = self.service_parameters_mllib['nclasses']
        self.predict_parameters_input = {}
        self.predict_parameters_mllib = {"gpu": self.service_parameters_mllib['gpu'],
                                         "gpuid ": self.service_parameters_mllib['gpuid']}
        self.predict_parameters_output = {'best': nclasses}

        json_dump = self.post_predict(self.sname, [svm_filepath], self.predict_parameters_input,
                                      self.predict_parameters_mllib, self.predict_parameters_output)

        self.answers.append(json_dump)
        with open("{}/model.json".format(self.model['repository'])) as f:
            self.calls = [json.loads(line, encoding='utf-8') for line in f]

        y_score = to_array(json_dump, nclasses)
        return y_score

    def predict(self, X):

        y_score = self.predict_proba(X)
        return (np.argmax(y_score, 1)).reshape(len(y_score), 1)


class MLPfromSVM(genericMLP):
    def __init__(self, host='localhost',
                 port=8080,
                 sname='',
                 mllib='caffe',
                 description='',
                 repository='',
                 templates='../templates/caffe',
                 connector='svm',
                 nclasses=None,
                 ntargets=None,
                 gpu=False,
                 gpuid=0,
                 template='mlp',
                 layers=[50],
                 activation='relu',
                 dropout=0.5,
                 regression=False,
                 finetuning=False,
                 db=True):
        super(MLPfromSVM, self).__init__(host=host,
                                         port=port,
                                         sname=sname,
                                         mllib=mllib,
                                         description=description,
                                         repository=repository,
                                         templates=templates,
                                         connector=connector,
                                         nclasses=nclasses,
                                         ntargets=ntargets,
                                         gpu=gpu,
                                         gpuid=gpuid,
                                         template=template,
                                         layers=layers,
                                         activation=activation,
                                         dropout=dropout,
                                         regression=regression,
                                         finetuning=finetuning,
                                         db=db)


class MLPfromArray(genericMLP):
    def __init__(self, host='localhost',
                 port=8080,
                 sname='',
                 mllib='caffe',
                 description='',
                 repository='',
                 templates='../templates/caffe',
                 connector='svm',
                 nclasses=None,
                 ntargets=None,
                 gpu=False,
                 gpuid=0,
                 template='mlp',
                 layers=[50],
                 activation='relu',
                 dropout=0.5,
                 regression=False,
                 finetuning=False,
                 db=True):
        super(MLPfromArray, self).__init__(host=host,
                                           port=port,
                                           sname=sname,
                                           mllib=mllib,
                                           description=description,
                                           repository=repository,
                                           templates=templates,
                                           connector=connector,
                                           nclasses=nclasses,
                                           ntargets=ntargets,
                                           gpu=gpu,
                                           gpuid=gpuid,
                                           template=template,
                                           layers=layers,
                                           activation=activation,
                                           dropout=dropout,
                                           regression=regression,
                                           finetuning=finetuning,
                                           db=db)

    def fit(self, X, Y, validation_data=None, iterations=100, test_interval=None, base_lr=0.1,
            solver_type='SGD', batch_size=128, metrics=['mcll', 'accp'], class_weights=None):

        self.filepaths = []
        train_f = os.path.join(self.data_folder, "x_train_{}.svm".format(time_utils.fulltimestamp()))
        dump_svmlight_file(X, Y, train_f)
        self.filepaths.append(train_f)

        if validation_data:
            for i, (x_val, y_val) in enumerate(validation_data):
                valid_f = os.path.join(self.data_folder, "x_val{}_{}.svm".format(i, time_utils.fulltimestamp()))
                dump_svmlight_file(x_val, y_val, valid_f)
                self.filepaths.append(valid_f)

        # df: True otherwise core dump when training on svm data
        self.train_parameters_input = {'db': True},
        self.train_parameters_output = {"measure": metrics},
        self.train_parameters_mllib = {
            'gpu': self.service_parameters_mllib['gpu'],
            'solver': {'iterations': iterations,
                       'test_interval': test_interval,
                       'base_lr': base_lr,
                       'solver_type': solver_type},
            'net': {'batch_size': batch_size},
            'class_weights': class_weights if class_weights else [1.] * self.service_parameters_mllib['nclasses']
        }

        self.post_train(self.sname,
                        self.filepaths,
                        self.train_parameters_input,
                        self.train_parameters_mllib,
                        self.train_parameters_output, async=True)
        time.sleep(1)

        train_status = ''
        while True:
            train_status = self.get_train(self.sname, job=1, timeout=2)
            if train_status['head']['status'] == 'running':
                print(train_status['body']['measure'])
            else:
                print(train_status)
                break

    def predict_proba(self, X):

        pred_f = os.path.join(self.data_folder, "x_pred{}_{}.svm".format(self.n_pred, time_utils.fulltimestamp()))
        dump_svmlight_file(X, [-1] * X.shape[0], pred_f)
        nclasses = self.service_parameters_mllib['nclasses']

        self.predict_parameters_input = {}
        self.predict_parameters_mllib = {"gpu": self.service_parameters_mllib['gpu'],
                                         "gpuid ": self.service_parameters_mllib['gpuid']}
        self.predict_parameters_output = {'best': nclasses}

        json_dump = self.post_predict(self.sname, [pred_f], self.predict_parameters_input,
                                      self.predict_parameters_mllib, self.predict_parameters_output)
        y_score = to_array(json_dump, nclasses)
        return y_score

    def predict(self, X):

        y_score = self.predict_proba(X)
        return (np.argmax(y_score, 1)).reshape(len(y_score), 1)