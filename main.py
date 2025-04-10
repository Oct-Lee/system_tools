import sys
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import QApplication
from gui import SystemCheckApp

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon("./bin/ubuntu_repair_tool.ico"))
    window = SystemCheckApp()
    window.show()
    sys.exit(app.exec_())
