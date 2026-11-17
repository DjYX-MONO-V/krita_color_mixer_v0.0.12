import colorsys
import math
from PyQt5.QtCore import QByteArray, QPointF, QRect, Qt, QTimer
from PyQt5.QtGui import QColor, QCursor, QImage, QMouseEvent, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from krita import (
    DockWidget,
    DockWidgetFactory,
    DockWidgetFactoryBase,
    Krita,
    ManagedColor,
)


# --- МАТЕМАТИКА ЦВЕТОВЫХ ПРОСТРАНСТВ И ГАРМОНИК ---
class ColorMath:

  @staticmethod
  def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

  @staticmethod
  def _linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    v = 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return int(round(max(0, min(255, v * 255))))

  @classmethod
  def rgb_to_oklch(cls, r, g, b):
    lr = cls._srgb_to_linear(r)
    lg = cls._srgb_to_linear(g)
    lb = cls._srgb_to_linear(b)

    l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb
    m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb
    s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb

    l_ = math.copysign(abs(l) ** (1 / 3), l)
    m_ = math.copysign(abs(m) ** (1 / 3), m)
    s_ = math.copysign(abs(s) ** (1 / 3), s)

    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_val = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    C = math.hypot(a, b_val)
    H = (math.degrees(math.atan2(b_val, a)) + 360) % 360
    return L, C, H

  @classmethod
  def oklch_to_rgb(cls, L, C, H):
    rad = math.radians(H)
    a = C * math.cos(rad)
    b_val = C * math.sin(rad)

    l_ = L + 0.3963377774 * a + 0.2158037573 * b_val
    m_ = L - 0.1055613458 * a - 0.0638541728 * b_val
    s_ = L - 0.0894841775 * a - 1.2914855480 * b_val

    l = l_ ** 3
    m = m_ ** 3
    s = s_ ** 3

    lr = +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    lg = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    lb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    return (
        cls._linear_to_srgb(lr),
        cls._linear_to_srgb(lg),
        cls._linear_to_srgb(lb),
    )

  @classmethod
  def rgb_to_lab(cls, r, g, b):
    lr = cls._srgb_to_linear(r)
    lg = cls._srgb_to_linear(g)
    lb = cls._srgb_to_linear(b)

    x = (lr * 0.4124564 + lg * 0.3575761 + lb * 0.1804375) / 0.95047
    y = (lr * 0.2126729 + lg * 0.7151522 + lb * 0.0721750) / 1.00000
    z = (lr * 0.0193339 + lg * 0.1191920 + lb * 0.9503041) / 1.08883

    def f(t):
      return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    fx, fy, fz = f(x), f(y), f(z)
    L = (116 * fy) - 16
    a = 500 * (fx - fy)
    b_val = 200 * (fy - fz)
    return L, a, b_val

  @classmethod
  def lab_to_rgb(cls, L, a, b_val):
    fy = (L + 16) / 116.0
    fx = a / 500.0 + fy
    fz = fy - b_val / 200.0

    def f_inv(t):
      return t ** 3 if (t ** 3) > 0.008856 else (t - 16 / 116) / 7.787

    x = f_inv(fx) * 0.95047
    y = f_inv(fy) * 1.00000
    z = f_inv(fz) * 1.08883

    lr = x * 3.2404542 + y * -1.5371385 + z * -0.4985314
    lg = x * -0.9692660 + y * 1.8760108 + z * 0.0415560
    lb = x * 0.0556434 + y * -0.2040259 + z * 1.0572252

    return (
        cls._linear_to_srgb(lr),
        cls._linear_to_srgb(lg),
        cls._linear_to_srgb(lb),
    )

  @classmethod
  def interpolate(cls, rgb1, rgb2, t, mode='OKLCH'):
    if mode == 'RGB':
      r = int(round(rgb1[0] + (rgb2[0] - rgb1[0]) * t))
      g = int(round(rgb1[1] + (rgb2[1] - rgb1[1]) * t))
      b = int(round(rgb1[2] + (rgb2[2] - rgb1[2]) * t))
      return r, g, b
    elif mode == 'LAB':
      L1, a1, b1 = cls.rgb_to_lab(*rgb1)
      L2, a2, b2 = cls.rgb_to_lab(*rgb2)
      L = L1 + (L2 - L1) * t
      a = a1 + (a2 - a1) * t
      b = b1 + (b2 - b1) * t
      return cls.lab_to_rgb(L, a, b)
    elif mode == 'OKLCH':
      L1, C1, H1 = cls.rgb_to_oklch(*rgb1)
      L2, C2, H2 = cls.rgb_to_oklch(*rgb2)
      L = L1 + (L2 - L1) * t
      C = C1 + (C2 - C1) * t
      if C1 < 0.005:
        H = H2
      elif C2 < 0.005:
        H = H1
      else:
        diff = ((H2 - H1 + 180) % 360) - 180
        H = (H1 + diff * t + 360) % 360
      return cls.oklch_to_rgb(L, C, H)
    return rgb1

  @classmethod
  def generate_harmonies(cls, rgb, harmony_type):
    h, s, v = colorsys.rgb_to_hsv(
        rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    )
    hues = [h]
    if harmony_type == 'Complementary':
      hues.append((h + 0.5) % 1.0)
    elif harmony_type == 'Triadic':
      hues.extend([(h + 1 / 3) % 1.0, (h + 2 / 3) % 1.0])
    elif harmony_type == 'Analogous':
      hues.extend([(h + 0.0833) % 1.0, (h - 0.0833) % 1.0])
    elif harmony_type == 'Split-Complementary':
      hues.extend([(h + 150 / 360) % 1.0, (h + 210 / 360) % 1.0])

    if harmony_type == 'Monochromatic':
      variants = [
          (s * 0.4, min(1.0, v * 1.3)),
          (s * 0.8, v),
          (s, max(0.2, v * 0.7)),
          (max(0.1, s * 0.3), max(0.1, v * 0.4)),
      ]
      return [
          tuple(int(channel * 255) for channel in colorsys.hsv_to_rgb(h, sat, val))
          for sat, val in variants
      ]

    colors = []
    for hue in hues:
      colors.append(
          tuple(
              int(channel * 255)
              for channel in colorsys.hsv_to_rgb(hue, s, v)
          )
      )
      colors.append(
          tuple(
              int(channel * 255)
              for channel in colorsys.hsv_to_rgb(
                  hue, max(0.1, s * 0.6), min(1.0, v * 1.2)
              )
          )
      )
    return colors


# --- ИНТЕГРАЦИЯ С КИСТЬЮ И СЛОЯМИ КРИТЫ ---
def set_krita_brush_color(rgb):
  try:
    win = Krita.instance().activeWindow()
    if not win or not win.activeView():
      return
    view = win.activeView()
    mc = ManagedColor('RGBA', 'U8', '')
    mc.setComponents([rgb[2] / 255.0, rgb[1] / 255.0, rgb[0] / 255.0, 1.0])
    view.setForeGroundColor(mc)
  except Exception as e:
    print(f'ColorMixer set color error: {e}')


def create_palette_image(colors_list, box_size=64):
  if not colors_list:
    raise ValueError('Палитра пуста.')

  image = QImage(
      len(colors_list) * box_size, box_size, QImage.Format_RGBA8888
  )
  image.fill(Qt.transparent)
  painter = QPainter(image)
  for index, color in enumerate(colors_list):
    painter.fillRect(
        index * box_size, 0, box_size, box_size,
        QColor(color[0], color[1], color[2]),
    )
  painter.end()
  return image


def format_color_text(rgb, mode):
  r, g, b = rgb
  if mode == 'RGB':
    return f'RGB({r}, {g}, {b})'
  if mode == 'HSL':
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return f'HSL({round(h * 360)}, {round(s * 100)}%, {round(l * 100)}%)'
  return f'#{r:02X}{g:02X}{b:02X}'


def relative_luminance(rgb):
  def linearize(channel):
    channel = channel / 255.0
    if channel <= 0.04045:
      return channel / 12.92
    return ((channel + 0.055) / 1.055) ** 2.4

  r, g, b = (linearize(channel) for channel in rgb)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(rgb1, rgb2):
  luminance1 = relative_luminance(rgb1)
  luminance2 = relative_luminance(rgb2)
  lighter, darker = max(luminance1, luminance2), min(luminance1, luminance2)
  return (lighter + 0.05) / (darker + 0.05)


def lab_color_difference(rgb1, rgb2):
  lab1 = ColorMath.rgb_to_lab(*rgb1)
  lab2 = ColorMath.rgb_to_lab(*rgb2)
  return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


def add_palette_layer_to_krita(colors_list):
  """Создает новый слой в активном документе Krita и рисует палитру 64x64 пикселя"""
  layer = None
  root = None
  layer_added = False
  try:
    krita_inst = Krita.instance()
    doc = krita_inst.activeDocument()
    if not doc:
      raise RuntimeError('Нет открытого документа Krita.')
    if not colors_list:
      raise RuntimeError('Палитра пуста.')

    img = create_palette_image(colors_list)
    total_width = img.width()
    total_height = img.height()

    rgba_data = bytearray(img.constBits().asstring(img.byteCount()))
    # Krita's RGBA/U8 paint device stores channels as BGRA bytes.
    for offset in range(0, len(rgba_data), 4):
      rgba_data[offset], rgba_data[offset + 2] = (
          rgba_data[offset + 2],
          rgba_data[offset],
      )
    pixel_data = QByteArray(bytes(rgba_data))
    if pixel_data.size() != total_width * total_height * 4:
      raise RuntimeError('Не удалось подготовить пиксели палитры.')

    root = doc.rootNode()
    layer = doc.createNode('Color Palette Layer', 'paintLayer')
    if not layer:
      raise RuntimeError('Krita не смогла создать растровый слой.')
    if not root.addChildNode(layer, None):
      raise RuntimeError('Krita не смогла добавить слой в документ.')
    layer_added = True

    profiles = krita_inst.profiles('RGBA', 'U8')
    srgb_profile = next(
        (
            profile
            for profile in profiles
            if 'srgb-elle-v2-srgbtrc' in profile.lower()
        ),
        None,
    )
    if not srgb_profile:
      srgb_profile = next(
          (
              profile
              for profile in profiles
              if 'srgb' in profile.lower()
              and 'g10' not in profile.lower()
              and 'linear' not in profile.lower()
          ),
          None,
      )
    if not srgb_profile:
      raise RuntimeError('В Krita не найден профиль RGBA/U8 sRGB.')
    if not layer.setColorSpace('RGBA', 'U8', srgb_profile):
      raise RuntimeError('Не удалось установить цветовое пространство RGBA/U8.')

    if not layer.setPixelData(pixel_data, 0, 0, total_width, total_height):
      raise RuntimeError('Krita не смогла записать цвета в слой.')
    doc.waitForDone()
    doc.setActiveNode(layer)
    doc.refreshProjection()
  except Exception as e:
    if root and layer and layer_added:
      root.removeChildNode(layer)
    raise RuntimeError(f'Не удалось добавить палитру в Krita: {e}') from e
  return True


def qRgba(r, g, b, a):
  return ((a & 0xff) << 24) | ((r & 0xff) << 16) | ((g & 0xff) << 8) | (b & 0xff)


# --- ШИНА ДАННЫХ ---
class ColorBus:
  color1 = (26, 5, 54)
  color2 = (59, 13, 107)
  current_palette = []
  subscribers = []

  @classmethod
  def register(cls, callback):
    if callback not in cls.subscribers:
      cls.subscribers.append(callback)

  @classmethod
  def notify(cls):
    for cb in cls.subscribers:
      cb()


# --- ГРАДИЕНТНЫЙ ВИДЖЕТ ---
class GradientWidget(QWidget):

  def __init__(self):
    super().__init__()
    self.setFixedHeight(24)
    self.mode = 'OKLCH'
    self.setStyleSheet(
        'border: 1px solid #3F3F46; background: #2E2E34; border-radius: 2px;'
    )

  def set_mode(self, mode):
    self.mode = mode
    self.update()

  def paintEvent(self, event):
    super().paintEvent(event)
    width = self.width()
    height = self.height()
    if width <= 1:
      return
    img = QImage(width, height, QImage.Format_ARGB32)
    for x in range(width):
      t = x / max(1, width - 1)
      r, g, b = ColorMath.interpolate(
          ColorBus.color1, ColorBus.color2, t, self.mode
      )
      color = QColor(r, g, b)
      for y in range(height):
        img.setPixelColor(x, y, color)
    painter = QPainter(self)
    painter.drawImage(0, 0, img)
    painter.end()


# --- АДАПТИВНЫЙ ВИДЖЕТ ВЫБОРА ЦВЕТА ---
class PyQtRadialColorPicker(QWidget):

  def __init__(
      self, color_index=1, title='Color', initial_hex='#1A0536',
      screen_pick_callback=None,
  ):
    super().__init__()
    self.color_index = color_index
    self.screen_pick_callback = screen_pick_callback
    self.radius = 55
    self.h, self.s, self.v = self._hex_to_hsv(initial_hex)

    layout = QVBoxLayout(self)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(4)

    header_layout = QHBoxLayout()
    header_layout.setContentsMargins(0, 0, 0, 0)
    title_lbl = QLabel(title)
    title_lbl.setStyleSheet('font-weight: bold; color: #F4F4F5; font-size: 9pt;')
    header_layout.addWidget(title_lbl)
    header_layout.addStretch()

    btn_pick_fg = QPushButton('💉')
    btn_pick_fg.setFixedSize(22, 18)
    btn_pick_fg.setToolTip('Взять цвет с любой точки экрана')
    btn_pick_fg.setStyleSheet(
        'background-color: #2E2E34; color: #F4F4F5; border: 1px solid #3F3F46;'
        ' border-radius: 2px; font-size: 8pt;'
    )
    btn_pick_fg.clicked.connect(
        lambda: self.screen_pick_callback(self.color_index)
        if self.screen_pick_callback else None
    )
    header_layout.addWidget(btn_pick_fg)
    layout.addLayout(header_layout)

    self.wheel_lbl = QLabel()
    self.wheel_lbl.setCursor(Qt.CrossCursor)
    self.wheel_lbl.mousePressEvent = self._on_wheel_click
    self.wheel_lbl.mouseMoveEvent = self._on_wheel_click
    layout.addWidget(self.wheel_lbl, alignment=Qt.AlignCenter)

    self.v_slider = QSlider(Qt.Horizontal)
    self.v_slider.setRange(0, 100)
    self.v_slider.setValue(int(self.v * 100))
    self.v_slider.valueChanged.connect(self._on_v_change)
    layout.addWidget(self.v_slider)

    input_layout = QHBoxLayout()
    input_layout.addWidget(QLabel('HEX:'))
    self.hex_edit = QLineEdit()
    self.hex_edit.setMaximumWidth(90)
    self.hex_edit.editingFinished.connect(self._on_hex_submitted)
    input_layout.addWidget(self.hex_edit)
    input_layout.addWidget(QLabel('RGB:'))
    self.rgb_edit = QLineEdit()
    self.rgb_edit.setMaximumWidth(100)
    self.rgb_edit.editingFinished.connect(self._on_rgb_submitted)
    input_layout.addWidget(self.rgb_edit)
    layout.addLayout(input_layout)

    self.hsl_label = QLabel()
    self.hsl_label.setStyleSheet('color: #A1A1AA; font-size: 8pt;')
    layout.addWidget(self.hsl_label)

    self._update_color_values()
    ColorBus.register(self.sync_from_bus)
    self._update_wheel_size()

  def resizeEvent(self, event):
    super().resizeEvent(event)
    self._update_wheel_size()

  def _update_wheel_size(self):
    avail_width = self.width() - 12
    self.radius = max(30, min(avail_width // 2, 65))
    self.wheel_lbl.setFixedSize(self.radius * 2, self.radius * 2)
    self._redraw_wheel()

  def _hex_to_hsv(self, hex_str):
    hex_str = hex_str.lstrip('#')
    return colorsys.rgb_to_hsv(
        int(hex_str[0:2], 16) / 255.0,
        int(hex_str[2:4], 16) / 255.0,
        int(hex_str[4:6], 16) / 255.0,
    )

  def _redraw_wheel(self):
    size = self.radius * 2
    if size <= 0:
      return
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    for y in range(size):
      for x in range(size):
        dx, dy = x - self.radius, y - self.radius
        dist = math.hypot(dx, dy)
        if dist <= self.radius:
          angle = (math.degrees(math.atan2(dy, dx)) + 360) % 360
          r, g, b = colorsys.hsv_to_rgb(angle / 360.0, dist / self.radius, self.v)
          img.setPixelColor(
              x, y, QColor(int(r * 255), int(g * 255), int(b * 255))
          )
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    angle = math.radians(self.h * 360)
    dist = self.s * self.radius
    mx = self.radius + dist * math.cos(angle)
    my = self.radius + dist * math.sin(angle)
    painter.setPen(
        QPen(Qt.white if self.v < 0.65 else Qt.black, 2, Qt.SolidLine)
    )
    painter.drawEllipse(QPointF(mx, my), 4, 4)
    painter.end()
    self.wheel_lbl.setPixmap(QPixmap.fromImage(img))

  def _on_wheel_click(self, event):
    dx, dy = event.x() - self.radius, event.y() - self.radius
    dist = min(math.hypot(dx, dy), self.radius)
    self.h = (math.degrees(math.atan2(dy, dx)) + 360) % 360 / 360.0
    self.s = dist / self.radius if self.radius > 0 else 0
    self._redraw_wheel()
    self._update_color_values()
    self._push_to_bus()

  def _on_v_change(self, val):
    self.v = val / 100.0
    self._redraw_wheel()
    self._update_color_values()
    self._push_to_bus()

  def get_rgb(self):
    r, g, b = colorsys.hsv_to_rgb(self.h, self.s, self.v)
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))

  def set_rgb(self, r, g, b):
    rgb = tuple(max(0, min(255, int(value))) for value in (r, g, b))
    self.h, self.s, self.v = colorsys.rgb_to_hsv(
        rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0
    )
    self.v_slider.blockSignals(True)
    self.v_slider.setValue(int(round(self.v * 100)))
    self.v_slider.blockSignals(False)
    self._redraw_wheel()
    self._update_color_values()
    self._push_to_bus()

  def _on_hex_submitted(self):
    value = self.hex_edit.text().strip().lstrip('#')
    if len(value) == 3 and all(c in '0123456789abcdefABCDEF' for c in value):
      value = ''.join(c * 2 for c in value)
    if len(value) == 6 and all(c in '0123456789abcdefABCDEF' for c in value):
      self.set_rgb(
          int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
      )
    else:
      self._update_color_values()

  def _on_rgb_submitted(self):
    value = (
        self.rgb_edit.text().lower().replace('rgb', '')
        .replace('(', '').replace(')', '')
    )
    parts = [
        part.strip() for part in value.replace(';', ',').split(',')
        if part.strip()
    ]
    if len(parts) == 3:
      try:
        self.set_rgb(*(int(part) for part in parts))
        return
      except ValueError:
        pass
    self._update_color_values()

  def _update_color_values(self):
    r, g, b = self.get_rgb()
    self.hex_edit.setText(f'#{r:02X}{g:02X}{b:02X}')
    self.rgb_edit.setText(f'{r}, {g}, {b}')
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    self.hsl_label.setText(
        f'HSL: {round(h * 360)}°, {round(s * 100)}%, {round(l * 100)}%'
    )

  def _push_to_bus(self):
    rgb = self.get_rgb()
    self._update_color_values()
    if self.color_index == 1:
      ColorBus.color1 = rgb
    else:
      ColorBus.color2 = rgb
    ColorBus.notify()

  def sync_from_bus(self):
    rgb = ColorBus.color1 if self.color_index == 1 else ColorBus.color2
    hsv = colorsys.rgb_to_hsv(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    if (
        abs(self.h - hsv[0]) > 0.001
        or abs(self.s - hsv[1]) > 0.001
        or abs(self.v - hsv[2]) > 0.001
    ):
      self.h, self.s, self.v = hsv
      self.v_slider.blockSignals(True)
      self.v_slider.setValue(int(self.v * 100))
      self.v_slider.blockSignals(False)
      self._redraw_wheel()
    self._update_color_values()


# --- ЕДИНЫЙ ГЛАВНЫЙ ДОКЕР (КРУГИ + ГРАДИЕНТ) ---
class ColorMixerStudioDocker(DockWidget):

  def __init__(self):
    super().__init__()
    self.setWindowTitle('Color Mixer Studio')
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(6)

    pickers_layout = QHBoxLayout()
    pickers_layout.setContentsMargins(0, 0, 0, 0)
    self.picker1 = PyQtRadialColorPicker(
        1, 'Start Color', '#1A0536', self.start_screen_pick
    )
    self.picker2 = PyQtRadialColorPicker(
        2, 'End Color', '#3B0D6B', self.start_screen_pick
    )
    pickers_layout.addWidget(self.picker1)
    pickers_layout.addWidget(self.picker2)
    layout.addLayout(pickers_layout)

    controls = QHBoxLayout()
    controls.setContentsMargins(0, 0, 0, 0)
    controls.addWidget(QLabel('Steps:'))
    self.steps_spin = QSpinBox()
    self.steps_spin.setRange(1, 15)
    self.steps_spin.setValue(3)
    self.steps_spin.valueChanged.connect(self.update_mixer)
    controls.addWidget(self.steps_spin)

    controls.addWidget(QLabel('Space:'))
    self.space_combo = QComboBox()
    self.space_combo.addItems(['OKLCH', 'LAB', 'RGB'])
    self.space_combo.currentIndexChanged.connect(self.update_mixer)
    controls.addWidget(self.space_combo)

    controls.addWidget(QLabel('Display:'))
    self.display_combo = QComboBox()
    self.display_combo.addItems(['HEX', 'RGB', 'HSL'])
    self.display_combo.currentIndexChanged.connect(self.update_mixer)
    controls.addWidget(self.display_combo)
    layout.addLayout(controls)

    self.grad_widget = GradientWidget()
    layout.addWidget(self.grad_widget)

    self.start_layout = QVBoxLayout()
    self.start_layout.setContentsMargins(0, 0, 0, 0)
    self.start_layout.setSpacing(2)
    layout.addLayout(self.start_layout)

    self.line1 = QFrame()
    self.line1.setFrameShape(QFrame.HLine)
    self.line1.setFrameShadow(QFrame.Sunken)
    layout.addWidget(self.line1)

    self.mid_layout = QVBoxLayout()
    self.mid_layout.setContentsMargins(0, 0, 0, 0)
    self.mid_layout.setSpacing(2)
    layout.addLayout(self.mid_layout)

    self.line2 = QFrame()
    self.line2.setFrameShape(QFrame.HLine)
    self.line2.setFrameShadow(QFrame.Sunken)
    layout.addWidget(self.line2)

    self.end_layout = QVBoxLayout()
    self.end_layout.setContentsMargins(0, 0, 0, 0)
    self.end_layout.setSpacing(2)
    layout.addLayout(self.end_layout)

    layout.addStretch()
    widget.setLayout(layout)
    scroll.setWidget(widget)
    self.setWidget(scroll)

    ColorBus.register(self.update_mixer)
    self.update_mixer()

  def create_row(self, col, is_endpoint=0):
    hex_val = f'#{col[0]:02X}{col[1]:02X}{col[2]:02X}'
    display_text = format_color_text(col, self.display_combo.currentText())
    row_widget = QWidget()
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 1, 0, 1)
    row_layout.setSpacing(6)

    swatch = QLabel()
    swatch.setFixedSize(16, 16)
    swatch.setStyleSheet(
        f'background-color: {hex_val}; border: 1px solid #3F3F46;'
    )

    suffix = (
        ' (Start Color)'
        if is_endpoint == 1
        else ' (End Color)'
        if is_endpoint == 2
        else ''
    )
    lbl = QLabel(display_text + suffix)
    lbl.setStyleSheet('font-family: Consolas; color: #F4F4F5; font-size: 9pt;')
    lbl.setCursor(Qt.PointingHandCursor)
    lbl.mousePressEvent = (
        lambda event, text=hex_val: QApplication.clipboard().setText(text)
    )

    btn_apply = QPushButton('🖌️')
    btn_apply.setFixedSize(22, 18)
    btn_apply.setToolTip('Применить цвет к активной кисти Krita')
    btn_apply.setStyleSheet(
        'background-color: #2E2E34; color: #F4F4F5; border: 1px solid'
        ' #3F3F46; border-radius: 2px; font-size: 8pt;'
    )
    btn_apply.clicked.connect(
        lambda checked, c=col, h=hex_val: (
            set_krita_brush_color(c),
            QApplication.clipboard().setText(h),
        )
    )

    row_layout.addWidget(swatch)
    row_layout.addWidget(lbl)
    row_layout.addStretch()
    row_layout.addWidget(btn_apply)
    return row_widget

  def update_mixer(self):
    for l_box in [self.start_layout, self.mid_layout, self.end_layout]:
      while l_box.count():
        item = l_box.takeAt(0)
        if item.widget():
          item.widget().deleteLater()

    steps = self.steps_spin.value()
    mode = self.space_combo.currentText()
    self.grad_widget.set_mode(mode)
    self.grad_widget.update()

    rgb1, rgb2 = ColorBus.color1, ColorBus.color2

    self.start_layout.addWidget(self.create_row(rgb1, is_endpoint=1))

    for i in range(1, steps + 1):
      t = i / (steps + 1)
      col = ColorMath.interpolate(rgb1, rgb2, t, mode)
      self.mid_layout.addWidget(self.create_row(col, is_endpoint=0))

    self.end_layout.addWidget(self.create_row(rgb2, is_endpoint=2))

  def start_screen_pick(self, color_index):
    self.hide()
    QTimer.singleShot(
        250,
        lambda: self._open_screen_overlay(
            'pick', lambda result, data: self._on_screen_pick(color_index, result, data)
        ),
    )

  def _open_screen_overlay(self, mode, callback):
    try:
      screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
      screenshot = screen.grabWindow(0)
      if screenshot.isNull():
        raise RuntimeError('Не удалось получить изображение экрана.')
      self.screen_overlay = ScreenCaptureOverlay(screenshot, mode, callback)
      self.screen_overlay.showFullScreen()
    except Exception as error:
      self.show()
      QMessageBox.warning(self, 'Color Mixer', str(error))

  def _on_screen_pick(self, color_index, result, data):
    self.show()
    if result == 'pick':
      picker = self.picker1 if color_index == 1 else self.picker2
      picker.set_rgb(*data)

  def canvasChanged(self, canvas):
    pass


# --- КАСТОМНЫЙ ВИДЖЕТ ПРЕВЬЮ КАРТИНКИ С КЛИКАТЕЛЬНОЙ ПИПЕТКОЙ ---
class ImagePreviewLabel(QLabel):

  def __init__(self, parent_docker):
    super().__init__()
    self.parent_docker = parent_docker
    self.original_pixmap = None
    self.setAlignment(Qt.AlignCenter)
    self.setCursor(Qt.CrossCursor)
    self.setStyleSheet(
        'border: 1px dashed #3F3F46; background: #222226; color: #71717A;'
        ' border-radius: 2px;'
    )
    self.setText('No Image Loaded')
    self.setMinimumHeight(100)

  def set_image(self, pixmap):
    self.original_pixmap = pixmap
    self.update_scaled_image()

  def update_scaled_image(self):
    if self.original_pixmap and not self.original_pixmap.isNull():
      scaled = self.original_pixmap.scaled(
          max(10, self.width() - 8),
          150,
          Qt.KeepAspectRatio,
          Qt.SmoothTransformation,
      )
      self.setPixmap(scaled)

  def resizeEvent(self, event):
    super().resizeEvent(event)
    self.update_scaled_image()

  def mousePressEvent(self, event: QMouseEvent):
    if self.original_pixmap and not self.original_pixmap.isNull() and self.pixmap():
      p = event.pos()
      pix_rect = self.pixmap().rect()
      x_offset = (self.width() - pix_rect.width()) // 2
      y_offset = (self.height() - pix_rect.height()) // 2

      local_x = p.x() - x_offset
      local_y = p.y() - y_offset

      if 0 <= local_x < pix_rect.width() and 0 <= local_y < pix_rect.height():
        orig_img = self.original_pixmap.toImage()
        orig_x = int(local_x * (orig_img.width() / pix_rect.width()))
        orig_y = int(local_y * (orig_img.height() / pix_rect.height()))

        if 0 <= orig_x < orig_img.width() and 0 <= orig_y < orig_img.height():
          qcol = orig_img.pixelColor(orig_x, orig_y)
          rgb = (qcol.red(), qcol.green(), qcol.blue())
          self.parent_docker.handle_preview_color(rgb)


class ScreenCaptureOverlay(QLabel):

  def __init__(self, screenshot, mode, callback):
    super().__init__()
    self.mode = mode
    self.callback = callback
    self.start_point = None
    self.end_point = None
    self.setWindowFlags(
        Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
    )
    screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
    self.setGeometry(screen.geometry())
    self.screenshot = screenshot.scaled(
        screen.geometry().size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
    )
    self.screenshot.setDevicePixelRatio(1.0)
    self.setPixmap(self.screenshot)
    self.setFixedSize(screen.geometry().size())
    self.setCursor(Qt.CrossCursor)

  def mousePressEvent(self, event):
    if event.button() != Qt.LeftButton:
      self.close()
      self.callback('cancel', None)
      return
    self.start_point = event.pos()
    self.end_point = event.pos()
    if self.mode == 'pick':
      color = self.screenshot.toImage().pixelColor(event.pos())
      self.close()
      self.callback('pick', (color.red(), color.green(), color.blue()))
    else:
      self.update()

  def mouseMoveEvent(self, event):
    if self.start_point is not None:
      self.end_point = event.pos()
      self.update()

  def mouseReleaseEvent(self, event):
    if self.mode != 'snip' or self.start_point is None:
      return
    rect = QRect(self.start_point, event.pos()).normalized()
    if rect.width() < 2 or rect.height() < 2:
      self.close()
      self.callback('cancel', None)
      return
    crop = self.screenshot.copy(rect)
    self.close()
    self.callback('snip', crop)

  def paintEvent(self, event):
    super().paintEvent(event)
    if self.start_point is not None and self.end_point is not None:
      painter = QPainter(self)
      painter.setPen(QPen(Qt.white, 1, Qt.DashLine))
      painter.drawRect(QRect(self.start_point, self.end_point).normalized())
      painter.end()

  def keyPressEvent(self, event):
    if event.key() == Qt.Key_Escape:
      self.close()
      self.callback('cancel', None)
      return
    super().keyPressEvent(event)


# --- МОДУЛЬ 3: ДОКЕР ГАРМОНИК И ПАЛИТР С ПРЕВЬЮ И РУЧНЫМ СБОРОМ ---
class ColorPalettesDocker(DockWidget):

  def __init__(self):
    super().__init__()
    self.setWindowTitle('Color Mixer: Palettes')
    self.ref_image = None
    self.manual_palette_colors = [None] * 6
    self.active_manual_slot = 0

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(6)

    harm_layout = QHBoxLayout()
    harm_layout.setContentsMargins(0, 0, 0, 0)
    harm_layout.addWidget(QLabel('Harmony:'))
    self.harmony_combo = QComboBox()
    self.harmony_combo.addItems([
        'Complementary',
        'Triadic',
        'Analogous',
        'Split-Complementary',
        'Monochromatic',
    ])
    self.harmony_combo.currentIndexChanged.connect(self.update_palettes)
    harm_layout.addWidget(self.harmony_combo)
    layout.addLayout(harm_layout)

    self.preview_lbl = ImagePreviewLabel(self)
    layout.addWidget(self.preview_lbl)

    ref_btn_layout = QHBoxLayout()
    ref_btn_layout.setContentsMargins(0, 0, 0, 0)
    self.btn_load_ref = QPushButton('📁 Load Image')
    self.btn_load_ref.setStyleSheet(
        'background-color: #2E2E34; color: #F4F4F5; border: 1px solid #3F3F46;'
        ' border-radius: 2px;'
    )
    self.btn_load_ref.clicked.connect(self.load_reference_image)
    ref_btn_layout.addWidget(self.btn_load_ref)

    self.btn_snip = QPushButton('Snip Screen')
    self.btn_snip.clicked.connect(self.start_screen_snip)
    ref_btn_layout.addWidget(self.btn_snip)

    self.btn_clear_manual = QPushButton('Clear Manual')
    self.btn_clear_manual.setStyleSheet(
        'background-color: #2E2E34; color: #F4F4F5; border: 1px solid #3F3F46;'
        ' border-radius: 2px;'
    )
    self.btn_clear_manual.clicked.connect(self.clear_manual_palette)
    ref_btn_layout.addWidget(self.btn_clear_manual)
    layout.addLayout(ref_btn_layout)

    target_layout = QHBoxLayout()
    target_layout.addWidget(QLabel('Image mode:'))
    self.image_target_combo = QComboBox()
    self.image_target_combo.addItems([
        'Start Color',
        'End Color',
        'Extract Palette',
        'Custom Palette (Manual)',
    ])
    self.image_target_combo.currentIndexChanged.connect(self._on_image_mode_changed)
    target_layout.addWidget(self.image_target_combo)
    layout.addLayout(target_layout)

    self.manual_count_layout = QHBoxLayout()
    self.manual_count_layout.addWidget(QLabel('Manual slots:'))
    self.manual_count_spin = QSpinBox()
    self.manual_count_spin.setRange(2, 16)
    self.manual_count_spin.setValue(6)
    self.manual_count_spin.valueChanged.connect(self._on_manual_count_changed)
    self.manual_count_layout.addWidget(self.manual_count_spin)

    self.manual_slots_layout = QGridLayout()
    self.manual_slot_buttons = []
    self.manual_controls_widget = QWidget()
    manual_controls_layout = QVBoxLayout(self.manual_controls_widget)
    manual_controls_layout.setContentsMargins(0, 0, 0, 0)
    manual_controls_layout.addLayout(self.manual_count_layout)
    manual_controls_layout.addLayout(self.manual_slots_layout)
    layout.addWidget(self.manual_controls_widget)
    self._render_manual_slots()
    self.manual_controls_widget.hide()

    count_layout = QHBoxLayout()
    count_layout.setContentsMargins(0, 0, 0, 0)
    count_layout.addWidget(QLabel('Extract Colors:'))
    self.count_spin = QSpinBox()
    self.count_spin.setRange(2, 16)
    self.count_spin.setValue(6)
    self.count_spin.valueChanged.connect(self.update_palettes)
    count_layout.addWidget(self.count_spin)

    self.extraction_controls_widget = QWidget()
    extraction_controls_layout = QVBoxLayout(self.extraction_controls_widget)
    extraction_controls_layout.setContentsMargins(0, 0, 0, 0)
    extraction_controls_layout.addLayout(count_layout)

    sort_layout = QHBoxLayout()
    sort_layout.addWidget(QLabel('Sort extracted colors:'))
    self.extraction_sort_combo = QComboBox()
    self.extraction_sort_combo.addItems(['Frequency', 'Hue', 'Brightness'])
    self.extraction_sort_combo.currentIndexChanged.connect(self.update_palettes)
    sort_layout.addWidget(self.extraction_sort_combo)
    extraction_controls_layout.addLayout(sort_layout)

    tolerance_layout = QHBoxLayout()
    tolerance_label = QLabel('Merge tolerance:')
    tolerance_label.setToolTip(
        'CIE76 Delta E tolerance; 0 keeps exact colors only.'
    )
    tolerance_layout.addWidget(tolerance_label)
    self.merge_tolerance_slider = QSlider(Qt.Horizontal)
    self.merge_tolerance_slider.setRange(0, 40)
    self.merge_tolerance_slider.setValue(12)
    self.merge_tolerance_slider.setToolTip(
        'CIE76 Delta E: 0 keeps exact colors only; higher values merge more'
        ' similar colors.'
    )
    self.merge_tolerance_slider.valueChanged.connect(
        self._on_merge_tolerance_changed
    )
    tolerance_layout.addWidget(self.merge_tolerance_slider)
    self.merge_tolerance_value = QLabel('12')
    self.merge_tolerance_value.setMinimumWidth(22)
    tolerance_layout.addWidget(self.merge_tolerance_value)
    extraction_controls_layout.addLayout(tolerance_layout)
    layout.addWidget(self.extraction_controls_widget)
    self.extraction_controls_widget.hide()

    self.btn_export_layer = QPushButton('🎨 Add Palette as Layer')
    self.btn_export_layer.setStyleSheet(
        'background-color: #3B82F6; color: #FFFFFF; font-weight: bold; border:'
        ' none; border-radius: 2px; padding: 5px;'
    )
    self.btn_export_layer.clicked.connect(self.export_to_layer)
    layout.addWidget(self.btn_export_layer)

    self.btn_save_png = QPushButton('Save Palette as PNG')
    self.btn_save_png.clicked.connect(self.save_palette_png)
    layout.addWidget(self.btn_save_png)

    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    layout.addWidget(line)

    self.palette_layout = QVBoxLayout()
    self.palette_layout.setContentsMargins(0, 0, 0, 0)
    self.palette_layout.setSpacing(2)
    layout.addLayout(self.palette_layout)

    self._create_contrast_checker(layout)

    layout.addStretch()
    widget.setLayout(layout)
    scroll.setWidget(widget)
    self.setWidget(scroll)

    ColorBus.register(self.update_palettes)
    self.update_palettes()

  def load_reference_image(self):
    file_name, _ = QFileDialog.getOpenFileName(
        self,
        'Open Reference Image',
        '',
        'Images (*.png *.jpg *.jpeg *.bmp *.webp)',
    )
    if file_name:
      pixmap = QPixmap(file_name)
      if not pixmap.isNull():
        self.ref_image = pixmap
        self.preview_lbl.set_image(pixmap)
        if self.image_target_combo.currentText() == 'Custom Palette (Manual)':
          self.manual_palette_colors = [None] * self.manual_count_spin.value()
          self.active_manual_slot = 0
          self._render_manual_slots()
        self.update_palettes()

  def handle_preview_color(self, rgb):
    target = self.image_target_combo.currentText()
    if target == 'Extract Palette':
      return
    elif target == 'Custom Palette (Manual)':
      self._set_manual_palette_color(rgb)
    elif target == 'Start Color':
      ColorBus.color1 = tuple(rgb)
      ColorBus.notify()
    else:
      ColorBus.color2 = tuple(rgb)
      ColorBus.notify()

  def _on_image_mode_changed(self):
    target = self.image_target_combo.currentText()
    self.manual_controls_widget.setVisible(
        target == 'Custom Palette (Manual)'
    )
    self.extraction_controls_widget.setVisible(target == 'Extract Palette')
    self.preview_lbl.setCursor(
        Qt.ArrowCursor if target == 'Extract Palette' else Qt.CrossCursor
    )
    self.update_palettes()

  def _on_manual_count_changed(self, count):
    self.manual_palette_colors = (
        self.manual_palette_colors + [None] * count
    )[:count]
    if self.active_manual_slot >= count:
      self.active_manual_slot = count - 1
    self._render_manual_slots()
    self.update_palettes()

  def _on_merge_tolerance_changed(self, value):
    self.merge_tolerance_value.setText(str(value))
    self.update_palettes()

  def _create_contrast_checker(self, parent_layout):
    self.contrast_checker_widget = QWidget()
    checker_layout = QVBoxLayout(self.contrast_checker_widget)
    checker_layout.setContentsMargins(0, 0, 0, 0)
    checker_layout.addWidget(QLabel('Color difference and contrast'))

    pair_layout = QVBoxLayout()
    text_color_layout = QHBoxLayout()
    text_color_layout.addWidget(QLabel('Text color:'))
    self.contrast_color1_combo = QComboBox()
    self.contrast_color1_combo.currentIndexChanged.connect(
        self._update_contrast_check
    )
    text_color_layout.addWidget(self.contrast_color1_combo)
    pair_layout.addLayout(text_color_layout)

    background_layout = QHBoxLayout()
    background_layout.addWidget(QLabel('Background:'))
    self.contrast_color2_combo = QComboBox()
    self.contrast_color2_combo.currentIndexChanged.connect(
        self._update_contrast_check
    )
    background_layout.addWidget(self.contrast_color2_combo)
    pair_layout.addLayout(background_layout)
    checker_layout.addLayout(pair_layout)

    self.contrast_preview = QLabel('Aa 123')
    self.contrast_preview.setAlignment(Qt.AlignCenter)
    self.contrast_preview.setMinimumHeight(28)
    checker_layout.addWidget(self.contrast_preview)

    self.contrast_result_label = QLabel()
    self.contrast_result_label.setWordWrap(True)
    checker_layout.addWidget(self.contrast_result_label)
    parent_layout.addWidget(self.contrast_checker_widget)

  def _refresh_contrast_checker(self, colors):
    first_index = self.contrast_color1_combo.currentIndex()
    second_index = self.contrast_color2_combo.currentIndex()
    for combo in (self.contrast_color1_combo, self.contrast_color2_combo):
      combo.blockSignals(True)
      combo.clear()
      for index, color in enumerate(colors):
        combo.addItem(
            f'{index + 1}: #{color[0]:02X}{color[1]:02X}{color[2]:02X}'
        )
      combo.setEnabled(len(colors) >= 2)

    if len(colors) < 2:
      self.contrast_color1_combo.blockSignals(False)
      self.contrast_color2_combo.blockSignals(False)
      self.contrast_result_label.setText(
          'Add at least two colors to compare them.'
      )
      self.contrast_preview.setText('')
      self.contrast_preview.setStyleSheet('')
      return

    first_index = max(0, min(first_index, len(colors) - 1))
    second_index = max(0, min(second_index, len(colors) - 1))
    if first_index == second_index:
      second_index = (first_index + 1) % len(colors)
    self.contrast_color1_combo.setCurrentIndex(first_index)
    self.contrast_color2_combo.setCurrentIndex(second_index)
    self.contrast_color1_combo.blockSignals(False)
    self.contrast_color2_combo.blockSignals(False)
    self._update_contrast_check()

  def _update_contrast_check(self):
    colors = ColorBus.current_palette
    first_index = self.contrast_color1_combo.currentIndex()
    second_index = self.contrast_color2_combo.currentIndex()
    if (
        len(colors) < 2 or first_index < 0 or second_index < 0
    ):
      return
    if first_index == second_index:
      self.contrast_result_label.setText(
          'Choose two different colors to compare them.'
      )
      self.contrast_preview.setText('')
      self.contrast_preview.setStyleSheet('')
      return

    text_color = colors[first_index]
    background_color = colors[second_index]
    ratio = contrast_ratio(text_color, background_color)
    difference = lab_color_difference(text_color, background_color)
    if ratio >= 7:
      status = 'WCAG AAA for normal text'
    elif ratio >= 4.5:
      status = 'WCAG AA for normal text'
    elif ratio >= 3:
      status = 'WCAG AA for large text only'
    else:
      status = 'Below WCAG AA'
    self.contrast_result_label.setText(
        f'CIE76 color difference: {difference:.1f}  |  '
        f'Contrast: {ratio:.2f}:1 — {status}'
    )
    text_hex = f'#{text_color[0]:02X}{text_color[1]:02X}{text_color[2]:02X}'
    background_hex = (
        f'#{background_color[0]:02X}{background_color[1]:02X}'
        f'{background_color[2]:02X}'
    )
    self.contrast_preview.setText(
        f'{text_hex} on {background_hex} — Aa 123'
    )
    self.contrast_preview.setStyleSheet(
        f'color: {text_hex}; background-color: {background_hex};'
        ' border: 1px solid #3F3F46; padding: 4px;'
    )

  def _render_manual_slots(self):
    while self.manual_slots_layout.count():
      item = self.manual_slots_layout.takeAt(0)
      if item.widget():
        item.widget().deleteLater()
    self.manual_slot_buttons = []
    for index, color in enumerate(self.manual_palette_colors):
      button = QPushButton(str(index + 1))
      button.setFixedSize(28, 24)
      button.setToolTip(f'Ручной слот {index + 1}')
      background = (
          f'#{color[0]:02X}{color[1]:02X}{color[2]:02X}'
          if color is not None else '#2E2E34'
      )
      border = '#3B82F6' if index == self.active_manual_slot else '#3F3F46'
      button.setStyleSheet(
          f'background-color: {background}; border: 2px solid {border};'
      )
      button.clicked.connect(
          lambda checked=False, slot=index: self._select_manual_slot(slot)
      )
      self.manual_slot_buttons.append(button)
      self.manual_slots_layout.addWidget(button, index // 4, index % 4)

  def _select_manual_slot(self, index):
    self.active_manual_slot = index
    self._render_manual_slots()

  def _set_manual_palette_color(self, rgb):
    if not self.manual_palette_colors:
      return
    current_slot = self.active_manual_slot
    self.manual_palette_colors[current_slot] = tuple(rgb[:3])
    next_empty = next(
        (
            (current_slot + offset) % len(self.manual_palette_colors)
            for offset in range(1, len(self.manual_palette_colors) + 1)
            if self.manual_palette_colors[
                (current_slot + offset) % len(self.manual_palette_colors)
            ] is None
        ),
        None,
    )
    if next_empty is not None:
      self.active_manual_slot = next_empty
    self._render_manual_slots()
    self.update_palettes()

  def clear_manual_palette(self):
    self.manual_palette_colors = [None] * self.manual_count_spin.value()
    self.active_manual_slot = 0
    self._render_manual_slots()
    self.update_palettes()

  def start_screen_snip(self):
    self.hide()
    QTimer.singleShot(250, self._open_screen_snip)

  def _open_screen_snip(self):
    try:
      screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
      screenshot = screen.grabWindow(0)
      if screenshot.isNull():
        raise RuntimeError('Не удалось получить изображение экрана.')
      self.screen_overlay = ScreenCaptureOverlay(
          screenshot, 'snip', self._on_screen_snip_finished
      )
      self.screen_overlay.showFullScreen()
    except Exception as error:
      self.show()
      QMessageBox.warning(self, 'Color Mixer', str(error))

  def _on_screen_snip_finished(self, result, data):
    self.show()
    if result == 'snip':
      self.ref_image = data
      self.preview_lbl.set_image(data)
      if self.image_target_combo.currentText() == 'Custom Palette (Manual)':
        self.manual_palette_colors = [None] * self.manual_count_spin.value()
        self.active_manual_slot = 0
        self._render_manual_slots()
      self.update_palettes()

  def _extract_dominant_colors(
      self, image, target_count, merge_tolerance, sort_order
  ):
    sample = image.scaled(
        64, 64, Qt.IgnoreAspectRatio, Qt.FastTransformation
    )
    counts = {}
    for y in range(sample.height()):
      for x in range(sample.width()):
        color = sample.pixelColor(x, y)
        rgb = (color.red(), color.green(), color.blue())
        counts[rgb] = counts.get(rgb, 0) + 1

    clusters = []
    buckets = {}

    def bucket_for(lab):
      return tuple(math.floor(channel / merge_tolerance) for channel in lab)

    for rgb, count in sorted(
        counts.items(), key=lambda item: item[1], reverse=True
    ):
      lab = ColorMath.rgb_to_lab(*rgb)
      matching_cluster = None
      closest_distance = merge_tolerance
      if merge_tolerance > 0:
        bucket = bucket_for(lab)
        for delta_l in (-1, 0, 1):
          for delta_a in (-1, 0, 1):
            for delta_b in (-1, 0, 1):
              nearby_bucket = (
                  bucket[0] + delta_l,
                  bucket[1] + delta_a,
                  bucket[2] + delta_b,
              )
              for cluster in buckets.get(nearby_bucket, ()):
                distance = math.sqrt(
                    sum(
                        (candidate - center) ** 2
                        for candidate, center in zip(lab, cluster['lab'])
                    )
                )
                if distance <= closest_distance:
                  matching_cluster = cluster
                  closest_distance = distance

      if matching_cluster is None:
        cluster = {
            'rgb_sum': [channel * count for channel in rgb],
            'weight': count,
            'rgb': rgb,
            'lab': lab,
        }
        clusters.append(cluster)
        if merge_tolerance > 0:
          buckets.setdefault(bucket_for(lab), []).append(cluster)
        continue

      old_bucket = bucket_for(matching_cluster['lab'])
      matching_cluster['weight'] += count
      matching_cluster['rgb_sum'] = [
          total + channel * count
          for total, channel in zip(matching_cluster['rgb_sum'], rgb)
      ]
      matching_cluster['rgb'] = tuple(
          int(round(total / matching_cluster['weight']))
          for total in matching_cluster['rgb_sum']
      )
      matching_cluster['lab'] = ColorMath.rgb_to_lab(
          *matching_cluster['rgb']
      )
      new_bucket = bucket_for(matching_cluster['lab'])
      if old_bucket != new_bucket:
        buckets[old_bucket].remove(matching_cluster)
        if not buckets[old_bucket]:
          del buckets[old_bucket]
        buckets.setdefault(new_bucket, []).append(matching_cluster)

    clusters.sort(key=lambda cluster: cluster['weight'], reverse=True)
    clusters = clusters[:target_count]
    if sort_order == 'Hue':
      clusters.sort(
          key=lambda cluster: colorsys.rgb_to_hsv(
              *(channel / 255.0 for channel in cluster['rgb'])
          )[0]
      )
    elif sort_order == 'Brightness':
      clusters.sort(key=lambda cluster: relative_luminance(cluster['rgb']))
    return [cluster['rgb'] for cluster in clusters]

  def update_palettes(self):
    while self.palette_layout.count():
      item = self.palette_layout.takeAt(0)
      if item.widget():
        item.widget().deleteLater()

    palette_colors = []

    target = self.image_target_combo.currentText()
    if target == 'Custom Palette (Manual)':
      palette_colors = [
          color for color in self.manual_palette_colors if color is not None
      ]
    elif (
        target == 'Extract Palette' and self.ref_image
        and not self.ref_image.isNull()
    ):
      palette_colors = self._extract_dominant_colors(
          self.ref_image.toImage(),
          self.count_spin.value(),
          self.merge_tolerance_slider.value(),
          self.extraction_sort_combo.currentText(),
      )
    else:
      harmony_type = self.harmony_combo.currentText()
      base_color = ColorBus.color1
      palette_colors = ColorMath.generate_harmonies(base_color, harmony_type)

    ColorBus.current_palette = palette_colors
    self._refresh_contrast_checker(palette_colors)

    for col in palette_colors:
      hex_val = f'#{col[0]:02X}{col[1]:02X}{col[2]:02X}'
      row_widget = QWidget()
      row_layout = QHBoxLayout(row_widget)
      row_layout.setContentsMargins(0, 1, 0, 1)
      row_layout.setSpacing(6)

      swatch = QLabel()
      swatch.setFixedSize(20, 18)
      swatch.setStyleSheet(
          f'background-color: {hex_val}; border: 1px solid #3F3F46;'
      )

      lbl = QLabel(hex_val)
      lbl.setStyleSheet(
          'font-family: Consolas; color: #F4F4F5; font-size: 9pt;'
      )
      lbl.setCursor(Qt.PointingHandCursor)
      lbl.mousePressEvent = (
          lambda event, text=hex_val: QApplication.clipboard().setText(text)
      )

      btn_apply = QPushButton('🖌️')
      btn_apply.setFixedSize(22, 18)
      btn_apply.setToolTip('Применить цвет к кисти Krita')
      btn_apply.setStyleSheet(
          'background-color: #2E2E34; color: #F4F4F5; border: 1px solid'
          ' #3F3F46; border-radius: 2px; font-size: 8pt;'
      )
      btn_apply.clicked.connect(
          lambda checked, c=col, h=hex_val: (
              set_krita_brush_color(c),
              QApplication.clipboard().setText(h),
          )
      )

      row_layout.addWidget(swatch)
      row_layout.addWidget(lbl)
      row_layout.addStretch()
      row_layout.addWidget(btn_apply)
      self.palette_layout.addWidget(row_widget)

  def export_to_layer(self):
    if (
        self.image_target_combo.currentText() == 'Custom Palette (Manual)'
        and any(color is None for color in self.manual_palette_colors)
    ):
      QMessageBox.information(
          self, 'Manual Palette', 'Заполните все цветовые слоты.'
      )
      return
    try:
      add_palette_layer_to_krita(ColorBus.current_palette)
    except Exception as e:
      QMessageBox.warning(self, 'Color Mixer', str(e))
      return
    QMessageBox.information(
        self, 'Color Mixer', 'Палитра добавлена на активный слой.'
    )

  def save_palette_png(self):
    if (
        self.image_target_combo.currentText() == 'Custom Palette (Manual)'
        and any(color is None for color in self.manual_palette_colors)
    ):
      QMessageBox.information(
          self, 'Manual Palette', 'Заполните все цветовые слоты.'
      )
      return
    if not ColorBus.current_palette:
      QMessageBox.information(self, 'Color Mixer', 'Палитра пуста.')
      return
    file_name, _ = QFileDialog.getSaveFileName(
        self,
        'Save Palette as PNG',
        'color_palette.png',
        'PNG Image (*.png)',
    )
    if not file_name:
      return
    if not file_name.lower().endswith('.png'):
      file_name += '.png'
    if not create_palette_image(ColorBus.current_palette).save(file_name, 'PNG'):
      QMessageBox.warning(self, 'Color Mixer', 'Не удалось сохранить PNG.')
      return
    QMessageBox.information(self, 'Color Mixer', 'Палитра сохранена.')

  def canvasChanged(self, canvas):
    pass


# --- РЕГИСТРАЦИЯ ДОКЕРОВ В KRITA ---
Krita.instance().addDockWidgetFactory(
    DockWidgetFactory(
        'ColorMixerStudioDocker',
        DockWidgetFactoryBase.DockRight,
        ColorMixerStudioDocker,
    )
)
Krita.instance().addDockWidgetFactory(
    DockWidgetFactory(
        'ColorPalettesDocker',
        DockWidgetFactoryBase.DockRight,
        ColorPalettesDocker,
    )
)