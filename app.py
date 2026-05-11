import sys
from ui import QApplication, SpotlightLLM
from opencode import opencode_stream

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = SpotlightLLM(streamer=opencode_stream)
    ex.show()
    sys.exit(app.exec_())
