import numpy as np
import numpy.ma as ma
import logging
import yaml

from h5flow.core import H5FlowResource
from h5flow.core import resources

from proto_nd_flow.util.lut import LUT, write_lut, read_lut
from proto_nd_flow.util.compat import assert_compat_version
import proto_nd_flow.util.units as units


class Geometry(H5FlowResource):
    '''
        Provides helper functions for looking up geometric properties. 
        **!! All output attributes and datasets are saved in units of cm !!**

        Parameters:
         - ``path``: ``str``, path to stored geometry data within file
         - ``crs_geometry_file``: ``str``, path to yaml file describing charge readout system geometry
         - ``lrs_geometry_file``: ``str``, path to yaml file describing light readout system
         - ``beam_direction``: ``str``, Cartesian coordinate of beam direction, e.g. ``'x'``, ``'y'``, ``'z'``
         - ``drift_direction``: ``str``, Cartesian coordinate of drift direction, e.g. ``'x'``, ``'y'``, ``'z'``

        Provides (for charge geometry):
         - ``beam_direction``         [attr]: Cartesian coordinate of beam direction
         - ``drift_direction``        [attr]: Cartesian coordinate of drift direction
         - ``pixel_pitch``            [attr]: distance between pixel centers 
         - ``cathode_thickness``      [attr]: thickness of cathode [cm]
         - ``lar_detector_bounds``    [attr]: min and max xyz coordinates for full LAr detector [cm]
         - ``module_RO_bounds``       [attr]: min and max xyz coordinates for each pixel LArTPC module [cm]
         - ``max_drift_distance``     [attr]: max drift distance in each LArTPC (2 TPCs per module) [cm]   
         - ``pixel_coordinates_2D``   [dset]: lookup table for pixel coordinates in 2D pixel plane
         - ``tile_id``                [dset]: lookup table for io channel tile ids 
         - ``anode_drift_coordinate`` [dset]: lookup table for tile drift coordinate (x as of Spring 2023)
         - ``drift_dir``: lookup table for tile drift direction (either ±x direction as of Spring 2023)
         - ``in_fid()``: helper function for defining fiducial volumes
         - ``get_drift_coordinate()``: helper function for converting drift time to drift coordinate 
                                       (x as of Spring 2023)

        Provides (for light geometry):
         - ``tpc_id``: lookup table for TPC number for light detectors
         - ``det_id``: lookup table for detector number from adc, channel id
         - ``det_bounds``: lookup table for detector minimum and maximum corners light detectors
         - ``solid_angle()``: helper function for determining the solid angle of a given detector

        Example usage::

            from h5flow.core import resources

            resources['Geometry'].pixel_pitch

        Example config::

            resources:
                - classname: Geometry
                  params:
                    path: 'geometry_info'
                    det_geometry_file: 'data/prot_nd_flow/2x2.yaml'
                    crs_geometry_file: 'data/proto_nd_flow/multi_tile_layout-3.0.40.yaml'
                    lrs_geometry_file: 'data/proto_nd_flow/light_module_desc-0.0.0.yaml'

    '''
    class_version = '0.1.0'

    default_path = 'geometry_info'
    default_det_geometry_file = '-'
    default_crs_geometry_file = '-'
    default_lrs_geometry_file = '-'
    default_beam_direction    = 'z'
    default_drift_direction   = 'x'


    def __init__(self, **params):
        super(Geometry, self).__init__(**params)

        self.path = params.get('path', self.default_path)
        self.det_geometry_file = params.get('det_geometry_file', self.default_crs_geometry_file)
        self.crs_geometry_file = params.get('crs_geometry_file', self.default_crs_geometry_file)
        self.lrs_geometry_file = params.get('lrs_geometry_file', self.default_lrs_geometry_file)
        self.beam_direction = params.get('beam_direction', self.default_beam_direction)
        self.drift_direction = params.get('drift_direction', self.default_drift_direction)
        self._cathode_thickness = 0.0 # thickness of cathode [cm]
        self._lar_detector_bounds = None # min and max xyz coordinates for full LAr detector
        self._module_RO_bounds = None # min and max xyz coordinates for each pixel LArTPC module
        self._max_drift_distance = None # max drift distance in each LArTPC (2 TPCs per module)


    def init(self, source_name):
        super(Geometry, self).init(source_name)

        # create group (if not present)
        self.data_manager.set_attrs(self.path)
        # load data (if present)
        self.data = dict(self.data_manager.get_attrs(self.path))

        if not self.data:
            # first time loading geometry, save to file
            self.load_geometry()

            self.data_manager.set_attrs(self.path,
                                        classname=self.classname,
                                        class_version=self.class_version,
                                        pixel_pitch=self.pixel_pitch,
                                        cathode_thickness=self.cathode_thickness,
                                        lar_detector_bounds=self.lar_detector_bounds,
                                        module_RO_bounds=self.module_RO_bounds,
                                        max_drift_distance=self.max_drift_distance,
                                        crs_geometry_file=self.crs_geometry_file, 
                                        beam_direction=self.beam_direction,
                                        drift_direction=self.drift_direction
                                        )
            write_lut(self.data_manager, self.path, self.pixel_coordinates_2D, 'pixel_coordinates_2D')
            write_lut(self.data_manager, self.path, self.tile_id, 'tile_id')
            write_lut(self.data_manager, self.path, self.anode_drift_coordinate, 'anode_drift_coordinate')
            write_lut(self.data_manager, self.path, self.drift_dir, 'drift_dir')

            write_lut(self.data_manager, self.path, self.tpc_id, 'tpc_id')
            write_lut(self.data_manager, self.path, self.det_id, 'det_id')
            write_lut(self.data_manager, self.path, self.det_bounds, 'det_bounds')
        else:
            assert_compat_version(self.class_version, self.data['class_version'])

            # load geometry from file
            self._pixel_pitch = self.data['pixel_pitch']
            self._cathode_thickness = self.data['cathode_thickness']
            self._lar_detector_bounds = self.data['lar_detector_bounds']
            self._module_RO_bounds = self.data['module_RO_bounds']
            self._max_drift_distance = self.data['max_drift_distance']
            self._pixel_coordinates_2D = read_lut(self.data_manager, self.path, 'pixel_coordinates_2D')
            self._tile_id = read_lut(self.data_manager, self.path, 'tile_id')
            self._anode_drift_coordinate = read_lut(self.data_manager, self.path, 'anode_drift_coordinate')
            self._drift_dir = read_lut(self.data_manager, self.path, 'drift_dir')

            self._tpc_id = read_lut(self.data_manager, self.path, 'tpc_id')
            self._det_id = read_lut(self.data_manager, self.path, 'det_id')
            self._det_bounds = read_lut(self.data_manager, self.path, 'det_bounds')

        lut_size = (self.pixel_coordinates_2D.nbytes + self.tile_id.nbytes
                    + self.anode_drift_coordinate.nbytes + self.drift_dir.nbytes
                    + self.tpc_id.nbytes + self.det_id.nbytes
                    + self.det_bounds.nbytes) * 4

        if self.rank == 0:
            logging.info(f'Geometry LUT(s) size: {lut_size/1024/1024:0.02f}MB')


    ## Charge geometry methods ##
    @property
    def pixel_pitch(self):
        ''' Distance between pixel centers [cm] '''
        return self._pixel_pitch
    

    @property
    def cathode_thickness(self):
        ''' Thickness of cathode [cm] '''
        return self._cathode_thickness
    

    @property
    def lar_detector_bounds(self):
        '''
            Array of shape ``(2,3)`` representing the minimum xyz coordinate 
            and the maximum xyz coordinate for the full LAr detector being studied
            (e.g. single module, 2x2, ND-LAr, etc.) [cm]
        '''
        return self._lar_detector_bounds
    

    @property
    def module_RO_bounds(self):
        '''
            Array of active volume extent for each module shape: ``(# modules,2,3)`` 
            representing the minimum xyz coordinate and the maximum xyz coordinate  
            for each module in the LAr detector [cm]
        '''
        return self._module_RO_bounds


    @property
    def max_drift_distance(self):
        '''
            Maximum possible drift distance for ionization electrons in each TPC (2 TPCs
            per module). Assuming a zero-thickness cathode, this is the distance between 
            the cathode and one of the two anodes in a module [cm]
        '''
        return self._max_drift_distance
    

    @property
    def pixel_coordinates_2D(self):
        '''
            Lookup table for pixel coordinates (2D), usage::

                resource['Geometry'].pixel_coordinates_2D[(io_group,io_channel,chip_id,channel_id)]

        '''
        return self._pixel_coordinates_2D


    @property
    def tile_id(self):
        '''
            Lookup table for tile id, usage::

                resource['Geometry'].tile_id[(io_group,io_channel)]

        '''
        return self._tile_id


    @property
    def anode_drift_coordinate(self):
        '''
            Lookup table for anode drift coordinate, usage::

                resource['Geometry'].anode_drift_coordinate[(tile_id,)]

        '''
        return self._anode_drift_coordinate


    @property
    def drift_dir(self):
        '''
            Lookup table for drift direction, usage::

                resource['Geometry'].drift_dir[(tile_id,)]

        '''
        return self._drift_dir


    def in_fid(self, xyz, cathode_fid=0.0, field_cage_fid=0.0, anode_fid=0.0):
        '''
            Check if xyz point is contained in the specified fiducial volume

            :param xyz: point to check, array ``shape: (N,3)``

            :param cathode_fid: fiducial boundary for cathode and anode, ``float``, optional

            :param field_cage_fid: fiducial boundary for field cage walls, ``float``, optional

            :returns: boolean array, ``shape: (N,)``, True indicates point is within fiducial volume

        '''
        # Define xyz coordinates of fiducial boundaries
        fid_cathode = np.array([cathode_fid, field_cage_fid, field_cage_fid])
        fid_anode = np.array([anode_fid, field_cage_fid, field_cage_fid])

        # Define drift regions
        positive_drift_regions = self.module_RO_bounds
        negative_drift_regions = self.module_RO_bounds
        
        for i in range(len(self.module_RO_bounds)):
            positive_drift_regions[i][0][0] = positive_drift_regions[i][1][0] - self.max_drift_distance
            negative_drift_regions[i][1][0] = negative_drift_regions[i][0][0] + self.max_drift_distance
        
        # Define fiducial boundaries for each drift region
        fid_positive_drift = [np.array([fid_cathode, fid_anode]) for module in self.module_RO_bounds]
        fid_negative_drift = [np.array([fid_anode, fid_cathode]) for module in self.module_RO_bounds]

        # Check if coordinate is in fiducial volume for any drift region
        coord_in_positive_drift_fid = ma.concatenate([np.expand_dims(\
                                    (xyz < np.expand_dims(boundary[1] - fid_positive_drift[i][1], 0)) &\
                                    (xyz > np.expand_dims(boundary[0] + fid_positive_drift[i][0], 0)), axis=-1)\
                                    for i,boundary in enumerate(positive_drift_regions)], axis=-1)
        coord_in_negative_drift_fid = ma.concatenate([np.expand_dims(\
                                    (xyz < np.expand_dims(boundary[1] - fid_negative_drift[i][1], 0)) &\
                                    (xyz > np.expand_dims(boundary[0] + fid_negative_drift[i][0], 0)), axis=-1)\
                                    for i,boundary in enumerate(negative_drift_regions)], axis=-1)
        in_positive_fid = ma.all(coord_in_positive_drift_fid, axis=1)
        in_negative_fid = ma.all(coord_in_negative_drift_fid, axis=1)
        in_any_positive_fid = ma.any(in_positive_fid, axis=-1)
        in_any_negative_fid = ma.any(in_negative_fid, axis=-1)
        in_any_fid = in_any_positive_fid | in_any_negative_fid
        return in_any_fid


    def get_drift_coordinate(self, io_group, io_channel, drift):
        '''
            Convert a drift distance on a set of ``(io group, io channel)`` to
            the drift coordinate.

            :param io_group: io group to calculate z coordinate, ``shape: (N,)``

            :param io_channel: io channel to calculate z coordinate, ``shape: (N,)``

            :param drift: drift distance [mm], ``shape: (N,)``

            :returns: drift coordinate [mm], ``shape: (N,)``

        '''
        tile_id = self.tile_id[(io_group, io_channel)]
        anode_drift_coord = self.anode_drift_coordinate[(np.array(tile_id),)]
        drift_direction = self.drift_dir[(np.array(tile_id),)]

        return anode_drift_coord.reshape(drift.shape) + \
            drift_direction.reshape(drift.shape) * drift

    ## Light geometry methods ##
    @staticmethod
    def _rotate_pixel(pixel_pos, tile_orientation):
        return pixel_pos[0] * tile_orientation[2], pixel_pos[1] * tile_orientation[1]


    @property
    def tpc_id(self):
        '''
            Lookup table for TPC id, usage::

                resource['Geometry'].tpc_id[(adc_index, channel_index)]

        '''
        return self._tpc_id


    @property
    def det_id(self):
        '''
            Lookup table for detector id within a TPC, usage::

                resource['Geometry'].det_id[(adc_index, channel_index)]

        '''
        return self._det_id


    @property
    def det_bounds(self):
        '''
            Lookup table for detector min and max xyz coordinate, usage::

                resource['Geometry'].det_bounds[(tpc_id, det_id)]

        '''
        return self._det_bounds


    @staticmethod
    def _rect_solid_angle_sign(coord, rect_min, rect_max):
        overlapping = (coord >= rect_min) & (coord <= rect_max)
        inverted = np.abs(rect_min - coord) < np.abs(rect_max - coord)

        sign_min = overlapping + ~overlapping * (1 - 2*inverted)
        sign_max = overlapping + ~overlapping * (2*inverted - 1)

        return sign_min, sign_max


    def solid_angle(self, xyz, tpc_id, det_id):
        '''
        Calculate the solid angle of a rectangular detector ``det_id`` in TPC
        ``tpc_id`` as seen from the point ``xyz``, under the assumption
        that the detector is oriented along the drift direction

        Note: this method does not consider cathode / field cage visibilty.

        :param xyz: array shape: ``(N,3)``

        :param tpc_id: array shape: ``(M,)``

        :param det_id: array shape: ``(M,)``

        :returns: array shape: ``(N, M)``

        '''
        x,y,z = xyz[...,0:1,np.newaxis], xyz[...,1:2,np.newaxis], xyz[...,2:3,np.newaxis]
        det_bounds = self.det_bounds[(tpc_id, det_id)]
        det_bounds = det_bounds.reshape((1,)+det_bounds.shape)
        det_min = det_bounds[...,0,:]
        det_max = det_bounds[...,1,:]

        det_x = (det_min[...,0] + det_max[...,0])/2
        det_y_sign_min, det_y_sign_max = self._rect_solid_angle_sign(
            y, det_min[...,1], det_max[...,1])
        det_z_sign_min, det_z_sign_max = self._rect_solid_angle_sign(
            z, det_min[...,2], det_max[...,2])

        omega = np.zeros(det_y_sign_min.shape, dtype=float)
        for det_y,det_y_sign in ((det_max[...,1], det_y_sign_max), (det_min[...,1], det_y_sign_min)):
            for det_z,det_z_sign in ((det_max[...,2], det_z_sign_max), (det_min[...,2], det_z_sign_min)):
                d = np.sqrt((x-det_x)**2 + (y-det_y)**2 + (z-det_z)**2)
                omega += det_y_sign * det_z_sign * np.arctan2(np.abs(det_y-y) * np.abs(det_z-z), np.abs(det_x-x)* d)

        return omega


    ## Load light and charge geometry ##
    def load_geometry(self):
        self._load_charge_geometry()
        self._load_light_geometry()


    def _load_light_geometry(self):
        if self.rank == 0:
            logging.warning(f'Loading geometry from {self.lrs_geometry_file}...')

        with open(self.lrs_geometry_file) as gf:
            geometry = yaml.load(gf, Loader=yaml.FullLoader)

        # enforce that light geometry formatting is as expected
        assert_compat_version(geometry['format_version'], '0.0.0')

        tpc_ids = np.array([v for v in geometry['tpc_center'].keys()])
        det_ids = np.array([v for v in geometry['det_center'].keys()])
        max_chan = max([len(chan) for tpc in geometry['det_chan'].values() for chan in tpc.values()])

        shape = tpc_ids.shape + det_ids.shape
        det_adc = np.full(shape, -1, dtype=int)
        det_chan = np.full(shape + (max_chan,), -1, dtype=int)
        det_chan_mask = np.zeros(shape + (max_chan,), dtype=bool)
        det_bounds = np.zeros(shape + (2,3), dtype=float)
        for i, tpc in enumerate(tpc_ids):
            for j, det in enumerate(det_ids):
                det_adc[i,j] = geometry['det_adc'][tpc][det]
                det_chan[i,j,:len(geometry['det_chan'][tpc][det])] = geometry['det_chan'][tpc][det]

                tpc_center = np.array(geometry['tpc_center'][tpc])
                det_geom = geometry['geom'][geometry['det_geom'][det]]
                det_center = np.array(geometry['det_center'][det])
                det_bounds[i,j,0] = tpc_center + det_center + np.array(det_geom['min'])
                det_bounds[i,j,1] = tpc_center + det_center + np.array(det_geom['max'])

        det_chan_mask = det_chan != -1

        det_adc, det_chan, tpc_ids, det_ids = np.broadcast_arrays(
            det_adc[...,np.newaxis], det_chan,
            tpc_ids[...,np.newaxis,np.newaxis], det_ids[...,np.newaxis])

        adc_chan_min_max = [(min(det_adc[det_chan_mask]), max(det_adc[det_chan_mask])),
                            (min(det_chan[det_chan_mask]), max(det_chan[det_chan_mask]))]
        self._tpc_id = LUT('i4', *adc_chan_min_max)
        self._tpc_id.default = -1

        self._det_id = LUT('i4', *adc_chan_min_max)
        self._det_id.default = -1

        det_min_max = [(min(tpc_ids[det_chan_mask]), max(tpc_ids[det_chan_mask])),
                       (min(det_ids[det_chan_mask]), max(det_ids[det_chan_mask]))]
        self._det_bounds = LUT('f4', *det_min_max, shape=(2,3))
        self._det_bounds.default = 0.

        self._tpc_id[(det_adc[det_chan_mask], det_chan[det_chan_mask])] = tpc_ids[det_chan_mask]
        self._det_id[(det_adc[det_chan_mask], det_chan[det_chan_mask])] = det_ids[det_chan_mask]

        tpc_ids, det_ids, det_chan_mask = tpc_ids[...,0], det_ids[...,0], det_chan_mask[...,0]
        self._det_bounds[(tpc_ids[det_chan_mask], det_ids[det_chan_mask])] = det_bounds[det_chan_mask]


    def _load_charge_geometry(self):
        if self.rank == 0:
            logging.warning(f'Loading geometry from {self.crs_geometry_file}...')

        with open(self.crs_geometry_file) as gf:
            geometry_yaml = yaml.load(gf, Loader=yaml.FullLoader)

        with open(self.det_geometry_file) as dgf:
            det_geometry_yaml = yaml.load(dgf, Loader=yaml.FullLoader)

        if 'multitile_layout_version' not in geometry_yaml.keys():
            raise RuntimeError('Only multi-tile geometry configurations are accepted')

        self._pixel_pitch = geometry_yaml['pixel_pitch']
        self._max_drift_distance = det_geometry_yaml['drift_length'] * units.cm # det geo yaml is in cm; here we convert to mm
        chip_channel_to_position = geometry_yaml['chip_channel_to_position']
        tile_orientations = geometry_yaml['tile_orientations']
        tile_positions = geometry_yaml['tile_positions']
        mod_centers = det_geometry_yaml['tpc_offsets']
        tile_chip_to_io = geometry_yaml['tile_chip_to_io']
        module_to_io_groups = det_geometry_yaml['module_to_io_groups']

        zs = np.array(list(chip_channel_to_position.values()))[:, 0] * self.pixel_pitch
        ys = np.array(list(chip_channel_to_position.values()))[:, 1] * self.pixel_pitch
        z_size = max(zs) - min(zs) + self.pixel_pitch
        y_size = max(ys) - min(ys) + self.pixel_pitch

        tile_geometry = {}

        tiles = np.arange(1,len(geometry_yaml['tile_chip_to_io'])*len(det_geometry_yaml['module_to_io_groups'])+1)
        io_groups = [
            geometry_yaml['tile_chip_to_io'][tile][chip] // 1000 * (mod-1)*2
            for tile in geometry_yaml['tile_chip_to_io']
            for chip in geometry_yaml['tile_chip_to_io'][tile]
            for mod in module_to_io_groups
        ]
        io_channels = [
            geometry_yaml['tile_chip_to_io'][tile][chip] % 1000
            for tile in geometry_yaml['tile_chip_to_io']
            for chip in geometry_yaml['tile_chip_to_io'][tile]
            for mod in module_to_io_groups
        ]
        chip_ids = [
            chip_channel // 1000
            for chip_channel in geometry_yaml['chip_channel_to_position']
            for mod in module_to_io_groups
        ]
        channel_ids = [
            chip_channel % 1000
            for chip_channel in geometry_yaml['chip_channel_to_position']
            for mod in module_to_io_groups
        ]
 
        pixel_coordinates_2D_min_max = [(min(v), max(v)) for v in (io_groups, io_channels, chip_ids, channel_ids)]
        self._pixel_coordinates_2D = LUT('f4', *pixel_coordinates_2D_min_max, shape=(2,))
        self._pixel_coordinates_2D.default = 0.
    
        tile_min_max = [(min(v), len(module_to_io_groups)*max(v)) for v in (io_groups, io_channels)]
        self._tile_id = LUT('i4', *tile_min_max)
        self._tile_id.default = -1
    
        anode_min_max = [(min(tiles), len(module_to_io_groups)*max(tiles))]
        self._anode_drift_coordinate = LUT('f4', *anode_min_max)
        self._anode_drift_coordinate.default = 0.
        self._drift_dir = LUT('i1', *anode_min_max)
        self._drift_dir.default = 0.

        # Warning: number of tiles (16) and number of modules (4) are hard-coded here
        self._anode_drift_coordinate[(tiles,)] = [tile_positions[(tile-1)%16+1][0]+units.cm*mod_centers[((tile-1)//16)%4][0] for tile in tiles] # det geo yaml is in cm; here we convert to mm

        self._drift_dir[(tiles,)] = [tile_orientations[(tile-1)%16+1][0] for tile in tiles]
        self._module_RO_bounds = []

        # Loop through modules
        for module_id in module_to_io_groups:
            for tile in tile_chip_to_io:
                tile_orientation = tile_orientations[tile]
                tile_geometry[tile] = tile_positions[tile], tile_orientations[tile]

                for chip in tile_chip_to_io[tile]:
                    io_group_io_channel = tile_chip_to_io[tile][chip]
                    io_group = io_group_io_channel//1000 + (module_id-1)*len(det_geometry_yaml['module_to_io_groups'][module_id])
                    io_channel = io_group_io_channel % 1000
                    self._tile_id[([io_group], [io_channel])] = tile+(module_id-1)*len(tile_chip_to_io)

                for chip_channel in chip_channel_to_position:
                    chip = chip_channel // 1000
                    channel = chip_channel % 1000

                    try:
                        io_group_io_channel = tile_chip_to_io[tile][chip]
                    except KeyError:
                        continue

                    io_group = io_group_io_channel // 1000 + (module_id-1)*len(det_geometry_yaml['module_to_io_groups'][module_id])
                    io_channel = io_group_io_channel % 1000

                    z = chip_channel_to_position[chip_channel][0] * \
                        self.pixel_pitch - z_size / 2 + self.pixel_pitch / 2
                    y = chip_channel_to_position[chip_channel][1] * \
                        self.pixel_pitch - y_size / 2 + self.pixel_pitch / 2

                    z, y = self._rotate_pixel((z, y), tile_orientation)

                    z += tile_positions[tile][2]
                    y += tile_positions[tile][1]
                    z += mod_centers[module_id-1][2]*units.cm # det geo yaml is in cm; here we convert to mm 
                    y += mod_centers[module_id-1][1]*units.cm # det geo yaml is in cm; here we convert to mm
                    self._pixel_coordinates_2D[(io_group, io_channel, chip, channel)] = z, y

            io_group, io_channel, chip_id, channel_id = self.pixel_coordinates_2D.keys()
            min_x, max_x = -999999999, 999999999
            min_y, max_y = -999999999, 999999999
            min_z, max_z = -999999999, 999999999
            
            # Loop through io_groups
            for iog in module_to_io_groups[module_id]:
                
                mask = (io_group == iog)

                # Get zy coordinates for io_group
                zy = self.pixel_coordinates_2D[(io_group[mask], io_channel[mask], chip_id[mask], channel_id[mask])]
            
                if (abs(min_y) == 999999999) and (abs(max_y) == 999999999) \
                    and (abs(min_z) == 999999999) and (abs(max_z) == 999999999):

                    # Assign min and max y,z coordinates for initial io_group
                    min_y, max_y = zy[:,1].min(), zy[:,1].max()
                    min_z, max_z = zy[:,0].min(), zy[:,0].max()

                else:
                    # Update min and max y,z coordinates based on subsequent io_group
                    min_y, max_y = min(min_y, zy[:,1].min()), max(max_y, zy[:,1].max())
                    min_z, max_z = min(min_z, zy[:,0].min()), max(max_z, zy[:,0].max())

                # Get x coordinates for anode corresponding to io_group
                tile_id = self.tile_id[(io_group[mask], io_channel[mask])]
                anode_drift_coordinate = np.unique(self.anode_drift_coordinate[(tile_id,)])[0]

                if (abs(min_x) == 999999999) and (abs(max_x) == 999999999):

                    min_x, max_x = anode_drift_coordinate, anode_drift_coordinate

                else: 
                    min_x, max_x = min(min_x, anode_drift_coordinate), max(max_x, anode_drift_coordinate)


            # Append module boundaries to module readout bounds list
            self._module_RO_bounds.append(np.array([[min_x, min_y, min_z],
                                                    [max_x, max_y, max_z]]))
            
        self._module_RO_bounds = np.array(self._module_RO_bounds)
        print("Module_RO_Bounds Indexing Test Bounds[0]:", np.array([bound[0] for bound in self._module_RO_bounds]))
        print("Module_RO_Bounds Indexing Test Bounds[1]:", np.array([bound[1] for bound in self._module_RO_bounds]))
        self._lar_detector_bounds = np.array([np.min(np.array([bound[0] for bound in self._module_RO_bounds]), axis=0),
                                              np.max(np.array([bound[1] for bound in self._module_RO_bounds]), axis=0)])
        
        cathode_x_coords = np.unique(np.array(mod_centers)[:,0])*10
        anode_to_cathode = np.min(np.array([abs(self._lar_detector_bounds[0][0] - cathode_x)
                                            for cathode_x in cathode_x_coords]))
        print("Anode to Cathode:", anode_to_cathode)
        if self._max_drift_distance < anode_to_cathode:
            # Difference b/w max drift dist and anode-cathode dist is 1/2 cathode thickness
            self._cathode_thickness = abs(anode_to_cathode - self._max_drift_distance) * 2.0
        else: 
            self._cathode_thickness = 0.0

        print("Module RO Bounds:", self._module_RO_bounds)
        print("LAr Detector Bounds:", self._lar_detector_bounds)
        print("Max Drift Distance:", self._max_drift_distance)
        print("Cathode Thickness:", self._cathode_thickness)
        print("Beam Direction:", self.beam_direction)
        print("Drift Direction:", self.drift_direction)