import numpy as np
import numpy.ma as ma
import os

from h5flow.core import H5FlowStage, resources
from h5flow import H5FLOW_MPI
import proto_nd_flow.util.units as units


class LightNoiseExtraction(H5FlowStage):
    '''
    Generate noise arrays for each optical channel. 
    Computes an average fft for each channel across all events in a file.

    Doesn't need to create references: only needs to output a file.

    Requires ``light/wvfm`` in the data cache.

    Also requires RunData resource in workflow.

    Example config::

        light_noise_extractor:
          classname: LightNoiseExtraction
          params:
            light_event_dset_name: 'light/events'
            light_wvfm_dset_name: 'light/wvfm'

    '''
    class_version = '0.0.1'

    default_unix_ts_window = 1  # how big of a symmetric window to use with unix timestamps (0=exact match, 1=±1 second, ...) [s]
    default_ts_window = 1000  # how big of a symmetric window to use with PPS timestamps (0=exact match, 10=±10 ticks, ...) [ticks]

    def __init__(self, **params):
        super(LightNoiseExtractor, self).__init__(**params)

        self.light_event_dset_name = params.get('light_event_dset_name')
        self.light_wvfm_dset_name = params.get('ligt_wvfm_dset_name')
        self.n_file = params.get('n_file', self.n_file)
        self.events_dset_name = None  # put off until init stage

        #self.unix_ts_window = params.get('unix_ts_window', self.default_unix_ts_window)
        #self.ts_window = params.get('ts_window', self.default_ts_window)

        #self.total_charge_events = 0
        #self.total_charge_triggers = 0
        #self.total_light_events = 0
        #self.total_matched_triggers = 0
        #self.total_matched_events = 0
        #self.matched_light = np.zeros((0,), dtype=bool)
        #self.total_matched_light = 0

    def init(self, source_name):
        super(LightNoiseExtraction, self).init(source_name)

        # save all config info
        self.events_dset_name = source_name
        self.data_manager.set_attrs(self.events_dset_name,
                                    charge_to_light_assoc_classname=self.classname,
                                    charge_to_light_assoc_class_version=self.class_version,
                                    light_event_dset=self.light_event_dset_name,
                                    charge_to_light_assoc_unix_ts_window=self.unix_ts_window,
                                    charge_to_light_assoc_ts_window=self.ts_window
                                    )

        # load in light system waveforms (only take 1000, since they take a lot of space)
        _, 
        
        # load in light system timestamps (use max to get non-null timestamp entries)
        self.light_event_id = self.data_manager.get_dset(self.light_event_dset_name)['id'][:]
        self.light_event_mask = self.data_manager.get_dset(self.light_event_dset_name)['wvfm_valid'][:].astype(bool)
        self.light_unix_ts = self.data_manager.get_dset(self.light_event_dset_name)['utime_ms'][:]
        self.light_unix_ts = self.light_unix_ts.mean(axis=-1)
        # reshape unix ts array to use with mask
        # self.light_unix_ts = self.light_unix_ts[:, :, np.newaxis]
        # self.light_unix_ts = np.where(self.light_event_mask, self.light_unix_ts, 0)
        # self.light_unix_ts = ma.array(self.light_unix_ts, mask=~self.light_event_mask).mean(axis=-1).mean(axis=-1)
        self.light_unix_ts = self.light_unix_ts * (units.ms / units.s)  # convert ms -> s
        self.light_ts = self.data_manager.get_dset(self.light_event_dset_name)['tai_ns'][:]
        self.light_ts = self.light_ts.mean(axis=-1)
        # reshape tai_ns array as above
        # self.light_ts = self.light_ts[:, :, np.newaxis]
        # self.light_ts =  np.where(self.light_event_mask, self.light_ts, 0)
        # self.light_ts = ma.array(self.light_ts, mask=~self.light_event_mask).mean(axis=-1).mean(axis=-1)
        if not resources['RunData'].is_mc:
            self.light_ts = self.light_ts % int(1e9)
        self.light_ts = self.light_ts * (units.ns / resources['RunData'].crs_ticks)  # convert ns -> larpix clock ticks

        self.light_unix_ts_start = self.light_unix_ts.min()
        self.light_unix_ts_end = self.light_unix_ts.max()
        self.total_light_events = len(self.light_unix_ts)
        self.matched_light = np.zeros((self.total_light_events,), dtype=bool)        

    def finish(self, source_name):
        super(LightNoiseExtraction, self).finish(source_name)
        
        if H5FLOW_MPI:
            self.total_charge_events = self.comm.reduce(self.total_charge_events, root=0)
            self.total_charge_triggers = self.comm.reduce(self.total_charge_triggers, root=0)
            self.total_matched_triggers = self.comm.reduce(self.total_matched_triggers, root=0)
            self.total_matched_events = self.comm.reduce(self.total_matched_events, root=0)
            self.matched_light = self.comm.reduce(self.matched_light, root=0)

        if self.rank == 0:
            self.total_matched_light = self.matched_light.clip(0,1).sum()
            trigger_eff = self.total_matched_triggers/max(self.total_charge_triggers, 1)
            event_eff = self.total_matched_events/max(self.total_charge_events, 1)
            light_eff = self.total_matched_light/max(self.total_light_events, 1)
            print(f'Total charge trigger matching: {self.total_matched_triggers}/{self.total_charge_triggers} ({trigger_eff:0.04f})')
            print(f'Total charge event matching: {self.total_matched_events}/{self.total_charge_events} ({event_eff:0.04f})')
            print(f'Total light event matching: {self.total_matched_light}/{self.total_light_events} ({light_eff:0.04f})') 

    def match_on_timestamp(self, charge_unix_ts, charge_pps_ts):
        unix_ts_start = charge_unix_ts.min()
        unix_ts_end = charge_unix_ts.max()  
        
        if self.light_unix_ts_start >= unix_ts_end + self.unix_ts_window or \
           self.light_unix_ts_end <= unix_ts_start - self.unix_ts_window:
            # no overlap, short circuit
            return np.empty((0, 2), dtype=int)

        # subselect only portion of light events that overlaps with unix timestamps
        i_min = np.argmax((self.light_unix_ts >= unix_ts_start - self.unix_ts_window))
        i_max = len(self.light_unix_ts) - np.argmax((self.light_unix_ts <= unix_ts_end + self.unix_ts_window)[::-1])
        sl = slice(i_min, i_max)
        assoc_mat = (np.abs(self.light_unix_ts[sl].reshape(1, -1) - charge_unix_ts.reshape(-1, 1)) <= self.unix_ts_window) \
                     & (np.abs(self.light_ts[sl].reshape(1, -1) - charge_pps_ts.reshape(-1, 1)) <= self.ts_window)
        idcs = np.argwhere(assoc_mat)
        if len(idcs):
            idcs[:, 1] = self.light_event_id[sl][idcs[:, 1]]  # idcs now contains ext trigger index <-> global light event id
        else:
            idcs = np.empty((0,2), dtype=int)

        return idcs
            
    def run(self, source_name, source_slice, cache):
        super(LightNoiseExtraction, self).run(source_name, source_slice, cache)

        event_data = cache[self.events_dset_name]
        ext_trigs_data = cache[self.ext_trigs_dset_name]
        ext_trigs_idcs = cache[self.ext_trigs_dset_name + '_idcs']
        ext_trigs_mask = ~rfn.structured_to_unstructured(ext_trigs_data.mask).any(axis=-1)

        nevents = len(event_data)
        ev_id = np.arange(source_slice.start, source_slice.stop, dtype=int)
        ext_trig_ref = np.empty((0, 2), dtype=int)
        ev_ref = np.empty((0, 2), dtype=int)        

        # check match on external triggers
        if nevents:
            ext_trigs_mask = ~rfn.structured_to_unstructured(ext_trigs_data.mask).any(axis=-1)
            if np.any(ext_trigs_mask):
                ext_trigs_all = ext_trigs_data.data[ext_trigs_mask]
                ext_trigs_idcs = ext_trigs_idcs.data[ext_trigs_mask]
                ext_trigs_unix_ts = np.broadcast_to(event_data['unix_ts'].reshape(-1, 1), ext_trigs_data.shape)[ext_trigs_mask]
                ext_trigs_ts = ext_trigs_all['ts']
                idcs = self.match_on_timestamp(ext_trigs_unix_ts, ext_trigs_ts)

                if len(idcs):
                    ext_trig_ref = np.append(ext_trig_ref, np.c_[ext_trigs_idcs[idcs[:, 0]], idcs[:, 1]], axis=0)
                    ev_id_bcast = np.broadcast_to(ev_id[:,np.newaxis], ext_trigs_mask.shape)
                    ev_ref = np.unique(np.append(ev_ref, np.c_[ev_id_bcast[ext_trigs_mask][idcs[:, 0]], idcs[:, 1]], axis=0), axis=0)

                logging.info(f'found charge/light match on {len(ext_trig_ref)}/{ext_trigs_mask.sum()} triggers')
                logging.info(f'found charge/light match on {len(ev_ref)}/{len(event_data)} events')
                self.total_charge_triggers += ext_trigs_mask.sum()
                self.total_matched_triggers += len(np.unique(ext_trig_ref[:,0]))
                self.total_matched_events += len(np.unique(ev_ref[:,0]))
                self.matched_light[np.unique(ext_trig_ref[:,1])] = True

        # write references
        # ext trig -> light event
        self.data_manager.write_ref(self.ext_trigs_dset_name, self.light_event_dset_name, ext_trig_ref)

        # charge event -> light event
        self.data_manager.write_ref(self.events_dset_name, self.light_event_dset_name, ev_ref)

        self.total_charge_events += len(event_data)
