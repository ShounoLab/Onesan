import sklearn.svm as SVM
from sklearn.model_selection import train_test_split
import sklearn.metrics
import copy
from tqdm import tqdm
from functools import reduce


def to_selectvec(code, Xdim):
    bcode = format(code, '0%db' % Xdim)
    return list(map(int, list(bcode)))


def pick_andvalue(X, code):
    slist = list()
    for i, b in enumerate(code):
        if b == 1:
            slist.append(i)

    return X[:, slist]


def calc_subset(subset, classifier, Xdim,
                X_train, Y_train, X_test, Y_test):
    result = list()

    for i in subset:
        classifier_print = copy.deepcopy(classifier)
        # train classifier
        classifier_print.fit(pick_andvalue(
            X_train, to_selectvec(i, Xdim)), Y_train)

        pred = classifier_print.predict(pick_andvalue(
            X_test, to_selectvec(i, Xdim)))

        accuracy = sklearn.metrics.accuracy_score(pred, Y_test)

        result.append([i, ''.join(map(str, to_selectvec(i, Xdim))),
                       accuracy])

    return result


def calc_subset_wrapper(params):
    return calc_subset(*params)


class Onesan(object):

    def __init__(self, X, Y, train_size=0.8, classifier=None,
                 classifier_param=None, n_onesan=1):

        # divide dataset into train and test
        self.X_train, self.X_test, self.Y_train, self.Y_test = \
            train_test_split(
                X, Y, test_size=1 - train_size
            )

        # number of dimensions
        self.Xdim = self.X_train.shape[-1]
        self.combinations = 2 ** self.Xdim

        # number of parallel processes
        self.n_onesan = n_onesan

        # set classifier
        if classifier is not None:
            if not hasattr(classifier, 'fit') or \
                    not hasattr(classifier, 'predict'):
                raise TypeError(
                    'classifier must have "fit" and "predict" method.'
                )

            self.classifier = classifier

        else:
            if classifier_param is None:
                self.classifier = SVM.LinearSVC(C=0.05, random_state=1,
                                                max_iter=5000)
            else:
                self.classifier = SVM.LinearSVC(**classifier_param)

    def __run_single_onesan(self):
        result = list()

        for i in tqdm(range(1, self.combinations)):
            classifier = copy.deepcopy(self.classifier)
            # train classifier
            classifier.fit(pick_andvalue(
                self.X_train, to_selectvec(i, self.Xdim)), self.Y_train)

            pred = classifier.predict(pick_andvalue(
                self.X_test, to_selectvec(i, self.Xdim)))

            accuracy = sklearn.metrics.accuracy_score(pred, self.Y_test)

            result.append([i, ''.join(map(str, to_selectvec(i, self.Xdim))),
                           accuracy])

    def __run_multiple_onesans(self):
        import multiprocessing as mp

        pools = mp.pool.Pool(self.n_onesan)

        targets = range(1, self.combinations)
        cellsize = int(self.combinations / self.n_onesan)
        tasks = [
            (targets[i * cellsize:i * cellsize + cellsize],
             self.classifier, self.Xdim, self.X_train, self.Y_train,
             self.X_test, self.Y_test) for i in range(self.n_onesan)]

        parallel_result = pools.map(calc_subset_wrapper, tasks)
        pools.close()

        result = reduce(lambda x, y: x + y, parallel_result)

        return result

    def run(self):

        if self.n_onesan <= 1:
            result = self.__run_single_onesan()

        else:
            result = self.__run_multiple_onesans()

        return sorted(result, key=lambda x: x[0])
