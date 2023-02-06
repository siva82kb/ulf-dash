"""Module containing temporary support fucnction for the ULFunc Analysis
Dashboard, which will eventually be moved to other modules.

Author: Sivakumar Balasubramanian
Email: siva82kb@gmail.com
Date: 03 Feb 2023
"""

import pandas
from pandas import DataFrame
from pandas import Timestamp, Timedelta
from datetime import datetime as dt
from scipy import signal
import datetime
import numpy as np


from monalysa import misc


class ARIMU(object):
    """Class to handle the raw IMU data from an ARIMU sensor.
    """
    
    @staticmethod
    def read_organize_data(filename, header=1):
        """Function to read CSV ARIMU data file.
        """
        _data = pandas.read_csv(filename, header=header, sep=",")
        _data.columns = [_c.strip() for _c in _data.columns]
        # Add a datetime columns
        _data['TimeStamp'] = _data['datetime'].map(lambda x: dt.strptime(x, "%Y-%m-%d %H:%M:%S.%f"))
        _data['Date'] = _data['TimeStamp'].map(lambda x: x.date())
        _data['Time'] = _data['TimeStamp'].map(lambda x: x.time())
        _data.drop(labels=['datetime'], axis='columns', inplace=True)
        return _data
    
    def __init__(self, filename: str, devid: str):
        """Class to handle data from an ActiGraph sensors. Each class must be provided with an string (devid).

        Parameters
        ----------
        filename : str
            Name of the filke with the ActiGraph data.
        devid : str
            A unique ID for the device assigned by the user.
        """
        self._filename = filename
        self._id = devid
        
        # Read and organize header string.
        with open(filename, "r") as fh:
            self._head_str = [fh.readline() for _ in range(1)]
        self._head_str[0] = " ".join(self._head_str[0].split(" ")[1:-1])
        
        # Read and organize csv data.
        self._data = ARIMU.read_organize_data(self._filename, header=1)
        
        # Sampling time of the data.
        self._samplingtime = self._data['TimeStamp'].diff().mode(dropna=True)[0].total_seconds()
        
    @property
    def filename(self):
        return self._filename
    
    @property
    def id(self):
        return self._id
    
    @property
    def head_str(self):
        return self._head_str
    
    @property
    def data(self):
        return self._data
    
    @property
    def dates(self):
        return self._data['Date'].unique()
    
    @property
    def columns(self):
        return self._data.columns

    @property
    def samplingtime(self):
        return self._samplingtime
    
    def get_data_between_timestamps(self, start: Timestamp, stop: Timestamp) -> DataFrame:
        """Returns a slice of the data between the given timestamps.

        Args:
            start (Timestamp): Start timestamp for slicing the data.
            stop (Timestamp): Stop timestamp for slicing the data.

        Returns:
            DataFrame: Dataframe containing the data between the given
            timestamps.
        """
        assert isinstance(start, Timestamp), "start must be a Timestamp"
        assert isinstance(stop, Timestamp), "stop must be a Timestamp"
        
        _inx = ((self._data['TimeStamp'] >= start)
                * (self._data['TimeStamp'] <= stop))
        return self._data[_inx]
    
    def get_date_time_segments(self, date: datetime.date) -> list[tuple[Timestamp, Timestamp]]:
        """Returns the start and end times of continuous time segments for
        the given date. A time segment is one where successive times points
        are not separated by more then 1 sec.

        Args:
            date (Timestamp.date): Date for which continuous time segments are
            to the identified.

        Returns:
            list[tuple[Timestamp, Timestamp]]: List of tuples with each
            containing two datetime time types. Each tuple indicates the start
            and end times for the continuous time segments found the data. 
        """
        assert isinstance(date, datetime.date),\
            'date should be an datetime date.'
        
        if date not in self.dates:
            return []
        
        return get_continuous_time_segments(
            timeseries=self._data[self._data['Date'] == date]['TimeStamp'],
            deltatime=pandas.Timedelta(self._samplingtime, "sec")
        )
    
    def get_all_time_segments(self) -> list[tuple[Timestamp, Timestamp]]:
        """Returns the start and end times of continuous time segments in the
        entire data. A time segment is one where successive times points
        are not separated by more then 1 sec.

        Returns:
            list[tuple[Timestamp, Timestamp]]: List of tuples with each
            containing two datetime time types. Each tuple indicates the start
            and end times for the continuous time segments found the data.
        """
        return get_continuous_time_segments(
            timeseries=self._data['TimeStamp'],
            deltatime=pandas.Timedelta(self._samplingtime, "sec")
        )

    def __len__(self):
        return len(self._data)
    
    def __repr__(self):
        return f"ActiGraphData(filename='{self._filename}', id='{self._id}')"


def from_gmac(acc_forearm, acc_ortho1, acc_ortho2, sampfreq, pitch_threshold=30, counts_threshold=0):
    """
    Computes UL use using the GMAC algorithm with pitch and counts estimated only from acceleration.
    Args:
        acc_forearm (np.array):  1D numpy array containing acceleration along the length of the forearm.
        acc_ortho1 (np.array): 1D numpy array containing acceleration along one of the orthogonal axis to the forearm.
        acc_ortho2 (np.array): 1D numpy array containing acceleration along the other orthogonal axis to the forearm.
        sampfreq (int): Sampling frequency of acceleration data.
        pitch_threshold (int): Pitch between +/- pitch_threshold are considered functional, default=30 (Leuenberger et al. 2017).
        counts_threshold (int): Counts greater than counts_threshold are considered functional, default=0 (optimized for youden index).

    Returns:
        tuple[np.array, np.array]: A tuple of 1D numpy arrays. The first 1D
        array is the list of time indices of the computed UL use signal. The
        second ID array is the UL use signal, which is a binary
        signal indicating the presence or absence of a "functional"
        movement any time instant.
    """
    assert len(acc_forearm) == len(acc_ortho1), "acc_forearm, acc_ortho1 and acc_ortho2 must be of equal length"
    assert len(acc_ortho1) == len(acc_ortho2), "acc_forearm, acc_ortho1 and acc_ortho2 must be of equal length"
    assert sampfreq > 0, "sampfreq must be a positive integer"

    # 1 second moving average filter
    acc_forearm = np.append(np.ones(sampfreq - 1) * acc_forearm[0], acc_forearm)  # padded at the beginning with the first value
    acc_forearm = np.convolve(acc_forearm, np.ones(sampfreq), 'valid') / sampfreq
    acc_forearm[acc_forearm < -1] = -1
    acc_forearm[acc_forearm > 1] = 1

    pitch_hat = -np.rad2deg(np.arccos(acc_forearm))
    # pitch_hat = -np.rad2deg(np.arccos(acc_forearm)) + 90

    hpf_cutoff = 1  # 1Hz high pass filter
    hfir = signal.firwin(25, hpf_cutoff, fs=sampfreq, pass_zero='highpass')
    acc_forearm_filt = signal.filtfilt(hfir, 1, acc_forearm)
    acc_ortho1_filt = signal.filtfilt(hfir, 1, acc_ortho1)
    acc_ortho2_filt = signal.filtfilt(hfir, 1, acc_ortho2)

    deadband_threshold = 0.068  # Brond et al. 2017
    acc_forearm_filt[np.abs(acc_forearm_filt) < deadband_threshold] = 0
    acc_ortho1_filt[np.abs(acc_ortho1_filt) < deadband_threshold] = 0
    acc_ortho2_filt[np.abs(acc_ortho2_filt) < deadband_threshold] = 0

    amag = [np.linalg.norm(x) for x in np.column_stack((acc_forearm_filt, acc_ortho1_filt, acc_ortho2_filt))]
    amag = [sum(amag[i:i + sampfreq]) for i in range(0, len(amag), sampfreq)]

    # 5 second moving average filter
    window = 5  # Bailey et al. 2014
    amag = np.append(np.ones(window - 1) * amag[0], amag)
    amag = np.convolve(amag, np.ones(window), 'valid') / window

    _uluse = [1 if np.abs(pitch) < pitch_threshold and count > counts_threshold else 0
                for pitch, count in zip(pitch_hat[0:len(pitch_hat):sampfreq], amag)]
    return (np.arange(len(_uluse)), _uluse)
    

def grav_sub_mag(acclmag: np.array, usesig: np.array,
                 nsample: int) -> tuple[np.array, np.array]:
    """Computes UL intensity from the raw acceleration signal from the ARIMU
    sensor.

    Parameters
    ----------
    acclmag : np.array
        1D numpy array containing the raw magnitude of the acceleration time series.
    usesig : np.array
        1D numpy array of the UL use binary signal.
    nsample : int
        The downsampling number for computing the instantaneous  UL intensity of use. This number must be equal to the ratio of the  sampling rate of the raw data (acclmag) and the uluse data. This means len(acclmag[::nsample]) == len(usesig).

    Returns
    -------
    tuple[np.array, np.array]
        A tuple of 1D numpy arrays. The first 1D array is the list of time indices of the computed UL use signal. The second ID array is the UL use signal, which is a binary signal indicating the presence or absence of a "functional" movement any time instant.
    """
    
    assert len(acclmag) > 0, "acclmag cannot be a of zero length."
    assert np.nanmin(acclmag) >= 0., "Vector magnitude cannot be negative."
    assert misc.is_binary_signal(usesig, allownan=True), "Use signal must be a binary signal."
    assert len(acclmag[::nsample]) == len(usesig), "The lengths of acclmag and usesig are not compatible."
    
    _n_acclmag = len(acclmag)
    _xval = np.arange(0, len(acclmag), nsample)
    _yval = np.mean(np.abs(acclmag - 1).reshape(_n_acclmag // nsample, nsample), axis=1) * usesig
    return (_xval, _yval)
