import * as monaco from 'monaco-editor';

// Basic Monaco setup
self.MonacoEnvironment = {
  getWorkerUrl: function (_moduleId, label) {
    if (label === 'json') {
      return './json.worker.bundle.js';
    }
    if (label === 'css' || label === 'scss' || label === 'less') {
      return './css.worker.bundle.js';
    }
    if (label === 'html' || label === 'handlebars' || label === 'razor') {
      return './html.worker.bundle.js';
    }
    if (label === 'typescript' || label === 'javascript') {
      return './ts.worker.bundle.js';
    }
    return './editor.worker.bundle.js';
  }
};

monaco.editor.defineTheme('lmms-dark', {
  base: 'vs-dark',
  inherit: true,
  rules: [],
  colors: {
    'editor.background': '#0d1117',
    'editor.lineHighlightBackground': '#161b22',
    'editorLineNumber.foreground': '#484f58',
    'editorIndentGuide.background': '#21262d',
    'editorIndentGuide.activeBackground': '#30363d'
  }
});

const editor = monaco.editor.create(document.getElementById('editor'), {
  value: '# Welcome to LMMs Editor\n',
  language: 'python',
  theme: 'lmms-dark',
  automaticLayout: true,
  minimap: {
    enabled: true
  }
});

// Setup QWebChannel API to bridge with Python
if (typeof QWebChannel !== 'undefined') {
  new QWebChannel(qt.webChannelTransport, function (channel) {
    window.pythonBridge = channel.objects.pythonBridge;
    
    // Subscribe to content changes from Python
    window.pythonBridge.setContent.connect(function (content, language) {
      if (language) {
        monaco.editor.setModelLanguage(editor.getModel(), language);
      }
      editor.setValue(content);
    });
    
    // Send content changes to Python
    editor.onDidChangeModelContent(() => {
      window.pythonBridge.onContentChanged(editor.getValue());
    });
    
    // Let Python know we are ready
    window.pythonBridge.onEditorReady();
  });
}

// Global accessor for debug/testing
window.editor = editor;
