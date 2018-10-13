from .qt import QtViewer
from .layouts import HorizontalLayout, VerticalLayout, StackedLayout

from ..layers import ImageLayer
from ..util.misc import (compute_max_shape as _compute_max_shape,
                         guess_metadata)


class Viewer:
    """Viewer object.

    Parameters
    ----------
    parent : Window
        Parent window.
    """
    _layout_map = {
        'horizontal': HorizontalLayout,
        'vertical': VerticalLayout,
        'stacked': StackedLayout
    }

    def __init__(self, window):
        self._window = window

        self._qt = QtViewer(self)

        # TODO: allow arbitrary display axis setting
        # self.y_axis = 0  # typically the y-axis
        # self.x_axis = 1  # typically the x-axis
        self.point = []
        self.layers = []
        self._layout = StackedLayout(self)

        self._max_dims = 0
        self._max_shape = tuple()

        # update flags
        self._child_image_changed = False
        self._need_redraw = False
        self._need_slider_update = False

        self._recalc_max_dims = False
        self._recalc_max_shape = False

    @property
    def window(self):
        """Window: Parent window.
        """
        return self._window

    @property
    def camera(self):
        """vispy.scene.Camera: Viewer camera.
        """
        return self._qt.view.camera

    @property
    def layout(self):
        """str: Layout display type.
        """
        for name, layout in self._layout_map.items():
            if isinstance(self._layout, layout):
                return name
        raise Exception()

    @layout.setter
    def layout(self, layout):
        if layout == self.layout:
            return

        layout = self._layout_map[layout].from_layout(self._layout)
        self._layout = layout
        self.reset_view()

    def _axis_to_row(self, axis):
        dims = len(self.point)
        message = f'axis {axis} out of bounds for {dims} dims'

        if axis < 0:
            axis = dims - axis
            if axis < 0:
                raise IndexError(message)
        elif axis >= dims:
            raise IndexError(message)

        if axis < 2:
            raise ValueError('cannot convert y/x-axes to rows')

        return axis - 1

    def add_image(self, image, meta):
        """Adds an image to the viewer.

        Parameters
        ----------
        image : np.ndarray
            Image data.
        meta : dict, optional
            Image metadata.

        Returns
        -------
        layer : ImageLayer
            Layer for the image.
        """
        layer = ImageLayer(image, meta, self)

        self.layers.append(layer)
        self._layout.add_layer(layer)

        self._child_image_changed = True
        self.update()

        return layer

    def imshow(self, image, meta=None, multichannel=None, **kwargs):
        """Shows an image in the viewer.

        Parameters
        ----------
        image : np.ndarray
            Image data.
        meta : dict, optional
            Image metadata.
        multichannel : bool, optional
            Whether the image is multichannel. Guesses if None.
        **kwargs : dict
            Parameters that will be translated to metadata.

        Returns
        -------
        layer : ImageLayer
            Layer for the image.
        """
        meta = guess_metadata(image, meta, multichannel, kwargs)

        return self.add_image(image, meta)

    def reset_view(self):
        """Resets the camera's view.
        """
        try:
            self.camera.set_range(*self._layout.view_range)
        except AttributeError:
            pass

    def _update_sliders(self):
        """Updates the sliders according to the contained images.
        """
        max_dims = self.max_dims
        max_shape = self.max_shape

        curr_dims = len(self.point)

        if curr_dims > max_dims:
            self.point = self.point[:max_dims]
            dims = curr_dims
        else:
            dims = max_dims
            self.point.extend([0] * (max_dims - curr_dims))

        for dim in range(2, dims):  # do not create sliders for y/x-axes
            try:
                dim_len = max_shape[dim]
            except IndexError:
                dim_len = 0

            self._qt.update_slider(dim, dim_len)

    def _update_layers(self):
        """Updates the contained layers.
        """
        for layer in self.layers:
            layer.set_view_slice(self.point)

    def _calc_max_dims(self):
        """Calculates the number of maximum dimensions in the contained images.
        """
        max_dims = 0

        for layer in self.layers:
            dims = layer.effective_ndim
            if dims > max_dims:
                max_dims = dims

        self._max_dims = max_dims

    def _calc_max_shape(self):
        """Calculates the maximum shape of the contained images.
        """
        shapes = (layer.image.shape for layer in self.layers)
        self._max_shape = _compute_max_shape(shapes, self.max_dims)

    def update(self):
        """Updates the viewer.
        """
        if self._child_image_changed:
            self._child_image_changed = False
            self._recalc_max_dims = True
            self._recalc_max_shape = True
            self._need_slider_update = True

            self._layout.update()
            self.reset_view()

        if self._need_redraw:
            self._need_redraw = False
            self._update_layers()

        if self._recalc_max_dims:
            self._recalc_max_dims = False
            self._calc_max_dims()

        if self._recalc_max_shape:
            self._recalc_max_shape = False
            self._calc_max_shape()

        if self._need_slider_update:
            self._need_slider_update = False
            self._update_sliders()

    def screenshot(self):
        """Renders the current canvas.

        Returns
        -------
        screenshot : np.ndarray
            View of the current canvas.
        """
        return self._qt.canvas.render()

    @property
    def max_dims(self):
        """int: Maximum tunable dimensions for contained images.
        """
        return self._max_dims

    @property
    def max_shape(self):
        """tuple: Maximum shape for contained images.
        """
        return self._max_shape