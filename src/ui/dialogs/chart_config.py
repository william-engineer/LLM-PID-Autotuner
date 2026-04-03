import random
import pyqtgraph as pg
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QGroupBox, QHBoxLayout, QGridLayout, 
                             QSpinBox, QLabel, QScrollArea, QWidget, QCheckBox, 
                             QLineEdit, QPushButton, QColorDialog)
from PyQt5.QtCore import QTimer

class ChartConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chart Configuration")
        self.setMinimumSize(500, 550)
        self.parent_app = parent
        
        # 继承主窗口的风格
        self.setStyleSheet(parent.styleSheet() + """
            QDialog { background-color: #0b0f19; }
            QCheckBox { color: #00ffcc; }
            QScrollArea { border: none; background-color: transparent; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
        """)

        char_config_layout = QVBoxLayout(self)

        # 轴设置
        group_axis = QGroupBox("Axis Settings")
        group_layout = QHBoxLayout()    
        grid_layout = QGridLayout()
        self.sp_y_min = QSpinBox(); self.sp_y_min.setRange(-1000, 1000)
        self.sp_y_max = QSpinBox(); self.sp_y_max.setRange(-1000, 1000)
        self.sp_x_min = QSpinBox(); self.sp_x_min.setRange(-1000, 1000)
        self.sp_x_max = QSpinBox(); self.sp_x_max.setRange(-1000, 1000)
        
        # 获取当前 Y 轴范围
        current_y_range = self.parent_app.plot_widget.viewRange()[1]
        self.sp_y_min.setValue(int(current_y_range[0]))
        self.sp_y_max.setValue(int(current_y_range[1]))
        
        # 获取当前 X 轴范围
        current_x_range = self.parent_app.plot_widget.viewRange()[0]
        self.sp_x_min.setValue(int(current_x_range[0]))
        self.sp_x_max.setValue(int(current_x_range[1]))
        self.x_min_backup = self.sp_x_min.value()
        self.x_max_backup = self.sp_x_max.value()

        grid_layout.addWidget(QLabel("X-Axis Min:"), 0, 0)
        grid_layout.addWidget(self.sp_x_min, 0, 1)
        grid_layout.addWidget(QLabel("Y-Axis Min:"), 0, 2)
        grid_layout.addWidget(self.sp_y_min, 0, 3)
        grid_layout.addWidget(QLabel("X-Axis Max:"), 1, 0)
        grid_layout.addWidget(self.sp_x_max, 1, 1)
        grid_layout.addWidget(QLabel("Y-Axis Max:"), 1, 2)
        grid_layout.addWidget(self.sp_y_max, 1, 3)
        grid_layout.setColumnStretch(0, 0)  # 标签列不拉伸
        grid_layout.setColumnStretch(1, 1)  # 输入框列可拉伸
        grid_layout.setColumnStretch(2, 0)  # 标签列不拉伸
        grid_layout.setColumnStretch(3, 1)  # 输入框列可拉伸

        group_layout.addLayout(grid_layout)
        group_axis.setLayout(group_layout)
        char_config_layout.addWidget(group_axis)

        # 曲线设置
        group_curves = QGroupBox("Curve Settings")
        curves_setting_layout = QVBoxLayout()
        
        # 曲线设置滚动区域
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.curves_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_area.setWidget(self.scroll_widget)
        curves_setting_layout.addWidget(self.scroll_area)

        # 添加新曲线的按钮
        btn_add_curve = QPushButton("+ Add New Curve")
        btn_add_curve.clicked.connect(self.add_new_curve)
        curves_setting_layout.addWidget(btn_add_curve)

        group_curves.setLayout(curves_setting_layout)
        char_config_layout.addWidget(group_curves)

        self.temp_next_id = self.parent_app.next_curve_id
        self.row_widgets = {} # id -> widgets dict
        self.ordered_ids = [] # 记录 UI 上的顺序

        # 提取主界面现有的曲线刷新曲线设置界面
        for curve_cfg in self.parent_app.curves:
            self.add_curve_row(curve_cfg)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("APPLY SETTINGS")
        btn_apply.clicked.connect(self.apply_settings)
        btn_cancel = QPushButton("CANCEL")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_cancel)
        char_config_layout.addLayout(btn_layout)

    def add_curve_row(self, curve_cfg):
        cid = curve_cfg['id']
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 5, 0, 5)

        # 显隐控制
        chk = QCheckBox()
        chk.setChecked(curve_cfg['visible'])
        
        # 名称编辑
        le = QLineEdit(curve_cfg['name'])
        
        # 颜色选择
        btn_color = QPushButton()
        btn_color.setMinimumSize(30, 20)
        btn_color.setStyleSheet(f"background-color: {curve_cfg['color']}; border: 1px solid white;")
        btn_color.clicked.connect(lambda _, b=btn_color, i=cid: self.pick_color(b, i))
        
        # 删除按钮
        btn_del = QPushButton("X")
        btn_del.setMinimumSize(30, 20)
        btn_del.setStyleSheet("background-color: #880000; color: white;")
        btn_del.clicked.connect(lambda _, i=cid: self.remove_curve_row(i))

        row_layout.addWidget(chk)
        row_layout.addWidget(le)
        row_layout.addWidget(btn_color)
        row_layout.addWidget(btn_del)

        self.curves_layout.addWidget(row_widget)

        self.row_widgets[cid] = {
            'main_widget': row_widget,
            'chk': chk,
            'le': le,
            'btn_color': btn_color,
            'color': curve_cfg['color']
        }
        self.ordered_ids.append(cid)

    def add_new_curve(self):
        # 随机生成一个颜色
        r = random.randint(50, 255)
        g = random.randint(50, 255)
        b = random.randint(50, 255)
        new_color = f"#{r:02x}{g:02x}{b:02x}"
        
        new_cfg = {
            'id': self.temp_next_id,
            'name': f'New Curve {self.temp_next_id}',
            'color': new_color,
            'visible': True,
            'type': 'normal',
            'abs_time': [],
            'x_data': [],
            'y_data': []
        }
        self.add_curve_row(new_cfg)
        self.temp_next_id += 1
        
        # 滚动到底部
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(self.scroll_area.verticalScrollBar().maximum()))

    def remove_curve_row(self, cid):
        if cid in self.row_widgets:
            widget_to_remove = self.row_widgets[cid]['main_widget']
            self.curves_layout.removeWidget(widget_to_remove)
            widget_to_remove.deleteLater()
            del self.row_widgets[cid]
            self.ordered_ids.remove(cid)

    def pick_color(self, btn, cid):
        color = QColorDialog.getColor()
        if color.isValid():
            hex_color = color.name()
            btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid white;")
            if cid in self.row_widgets:
                self.row_widgets[cid]['color'] = hex_color

    def apply_settings(self):
        self.parent_app.plot_widget.setYRange(self.sp_y_min.value(), self.sp_y_max.value())
        
        if self.sp_x_min.value() != self.x_min_backup or self.sp_x_max.value() != self.x_max_backup:
            self.parent_app.plot_widget.setXRange(self.sp_x_min.value(), self.sp_x_max.value())
        else:
            self.parent_app.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis)
            
        new_curves_list = []
        
        for cid in self.ordered_ids:
            widgets = self.row_widgets[cid]
            
            # 查找是否是已存在的曲线，保留其历史数据
            existing_type = 'normal'
            existing_abs = []
            existing_x = []
            existing_y = []
            for oc in self.parent_app.curves:
                if oc['id'] == cid:
                    existing_type = oc.get('type', 'normal')
                    existing_abs = oc.get('abs_time', [])
                    existing_x = oc['x_data']
                    existing_y = oc['y_data']
                    break
            
            new_curves_list.append({
                'id': cid,
                'name': widgets['le'].text(),
                'color': widgets['color'],
                'visible': widgets['chk'].isChecked(),
                'type': existing_type,
                'abs_time': existing_abs,
                'x_data': existing_x,
                'y_data': existing_y
            })

        self.parent_app.curves = new_curves_list
        self.parent_app.next_curve_id = self.temp_next_id
        self.parent_app.rebuild_plot()
        self.accept()
