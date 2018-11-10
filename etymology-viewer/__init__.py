from anki.hooks import addHook
from anki.utils import stripHTML
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView
import http
import urllib.request
import ssl

class EtymologyDefinition(object):
    def __init__(self, mw):
        self.mw = mw
        self.shown = False
        addHook('showQuestion', self._updateQ)
        addHook('showAnswer', self._updateA)
        addHook('deckClosing', self.hide)
        addHook('reviewCleanup', self.hide)

    def _addDockable(self, title, w):
        class DockableWithClose(QDockWidget):
            closed = pyqtSignal()

            def closeEvent(self, evt):
                self.closed.emit()
                QDockWidget.closeEvent(self, evt)

        dock = DockableWithClose(title, mw)
        dock.setObjectName(title)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetClosable)
        dock.setWidget(w)
        if mw.width() < 600:
            mw.resize(QSize(600, mw.height()))
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)
        return dock

    def _remDockable(self, dock):
        mw.removeDockWidget(dock)

    def show(self):
        if not self.shown:
            class ThinAnkiWebView(AnkiWebView):
                def sizeHint(self):
                    return QSize(200, 100)

            self.web = ThinAnkiWebView()
            self.shown = self._addDockable(_('Etymology Info'), self.web)
            self.shown.closed.connect(self._onClosed)
        self._update(self.mw.reviewer.state == 'answer')

    def hide(self):
        if self.shown:
            self._remDockable(self.shown)
            self.shown = None

    def toggle(self):
        if self.shown:
            self.hide()
        else:
            self.show()

    def _onClosed(self):
        # schedule removal for after evt has finished
        self.mw.progress.timer(100, self.hide, False)

    def _updateQ(self):
        self._update(False)

    def _updateA(self):
        self._update(True)

    def _update(self, show_answer):
        if not self.shown:
            return
        txt = ''
        r = self.mw.reviewer
        if r.card:
            word = r.card.q()
            txt += _('<h3>Etymology for %s</h3><br>' % word)
            if show_answer:
                definition = self._get_definition(word)
                txt += _('%s' % definition)
            else:
                txt += _('<i>Definition will be shown after you answer the card</i>')
        if not txt:
            txt = _('No current card.')
        style = self._style()
        self.web.setHtml('''
        <html><head>
        </head><style>%s</style>
        <body><center>%s</center></body></html>''' % (style, txt))

    def _style(self):
        from anki import version
        style = '* {font-family: sans-serif; }'
        if version.startswith('2.0.'):
            return style
        style += 'td { font-size: 80%; }'
        return style

    def _get_definition(self, word):
        # Sanitize string
        word = stripHTML(word)
        start_token = '<section class="word__defination--2q7ZH">'
        end_token = '</section>'
        context = ssl._create_unverified_context()
        url = 'https://www.etymonline.com/word/{}'.format(word)
        try:
            response = urllib.request.urlopen(url, context=context)
        except Exception:
            return 'No etymology entry found.'

        html = response.read().decode('utf-8')
        start = html.index(start_token) + len(start_token)
        end = html.index(end_token)
        return stripHTML(html[start:end])

_ed = EtymologyDefinition(mw)
def etymologyDefinition():
    _ed.toggle()

action = QAction(mw)
action.setText('Show/Hide Etymology')
action.setShortcut(QKeySequence('Ctrl+Shift+E'))
mw.form.menuTools.addAction(action)
action.triggered.connect(etymologyDefinition)