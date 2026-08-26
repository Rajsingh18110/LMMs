import * as monaco from 'monaco-editor';
import { initialize } from 'vscode/services';
import getBaseServiceOverride from '@codingame/monaco-vscode-base-service-override';
import getEnvironmentServiceOverride from '@codingame/monaco-vscode-environment-service-override';
import getExtensionsServiceOverride from '@codingame/monaco-vscode-extensions-service-override';
import getFilesServiceOverride from '@codingame/monaco-vscode-files-service-override';
import getHostServiceOverride from '@codingame/monaco-vscode-host-service-override';
import getLanguagesServiceOverride from '@codingame/monaco-vscode-languages-service-override';
import getLayoutServiceOverride from '@codingame/monaco-vscode-layout-service-override';
import getLocalizationServiceOverride from '@codingame/monaco-vscode-localization-service-override';
import getModelServiceOverride from '@codingame/monaco-vscode-model-service-override';
import getQuickAccessServiceOverride from '@codingame/monaco-vscode-quickaccess-service-override';
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

// Call initialize before creating the editor
await initialize({
  ...getBaseServiceOverride(),
  ...getEnvironmentServiceOverride(),
  ...getExtensionsServiceOverride(),
  ...getFilesServiceOverride(),
  ...getHostServiceOverride(),
  ...getLanguagesServiceOverride(),
  ...getLayoutServiceOverride(),
  ...getLocalizationServiceOverride(),
  ...getModelServiceOverride(),
  ...getQuickAccessServiceOverride({
    isKeybindingConfigurationVisible: () => true,
    shouldUseGlobalPicker: () => true
  })
});

// Since we are using layout service override with editorPart,
// we might not need to manually create the editor.
// Wait, actually `editorPart` only gives us a standard editor frame.
// We can still create our editor instance manually or retrieve it.
// Let's create it manually anyway for simplicity, though the DOM might conflict.
// If it conflicts, we should not use editorPart container.
const editor = monaco.editor.create(document.getElementById('editor'), {
  value: '# Welcome to LMMs Editor\n',
  language: 'python',
  theme: 'lmms-dark',
  automaticLayout: true,
  minimap: {
    enabled: true
  }
});

import { MonacoLanguageClient } from 'monaco-languageclient';

class BridgeMessageReader {
    constructor(bridge) {
        this.bridge = bridge;
        this.onError = () => ({ dispose: () => {} });
        this.onClose = () => ({ dispose: () => {} });
        this.onPartialMessage = () => ({ dispose: () => {} });
    }
    listen(callback) {
        const handler = (msg) => {
            try { callback(JSON.parse(msg)); } catch (e) { console.error(e); }
        };
        this.bridge.lspMessageFromJs.connect(handler);
        return { dispose: () => this.bridge.lspMessageFromJs.disconnect(handler) };
    }
    dispose() {}
}

class BridgeMessageWriter {
    constructor(bridge) {
        this.bridge = bridge;
        this.onError = () => ({ dispose: () => {} });
        this.onClose = () => ({ dispose: () => {} });
    }
    write(msg) {
        try {
            this.bridge.sendLspMessage(JSON.stringify(msg));
            return Promise.resolve();
        } catch(e) { return Promise.reject(e); }
    }
    end() {}
    dispose() {}
}

// Setup QWebChannel API to bridge with Python
if (typeof QWebChannel !== 'undefined') {
  new QWebChannel(qt.webChannelTransport, function (channel) {
    window.pythonBridge = channel.objects.pythonBridge;
    
    // Start LSP Client
    const languageClient = new MonacoLanguageClient({
        name: 'Python LSP Client',
        clientOptions: {
            documentSelector: ['python', 'javascript', 'typescript', 'json', 'css', 'html', 'markdown'],
            errorHandler: {
                error: () => ({ action: 1 }), // Continue
                closed: () => ({ action: 1 })
            }
        },
        connectionProvider: {
            get: () => Promise.resolve({
                reader: new BridgeMessageReader(window.pythonBridge),
                writer: new BridgeMessageWriter(window.pythonBridge)
            })
        }
    });
    
    languageClient.start().then(() => {
        console.log("LSP Client Started.");
    }).catch(err => {
        console.error("Failed to start LSP Client", err);
    });

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
    
    // Receive Git Decorations
    let gitDecorations = editor.createDecorationsCollection();
    window.pythonBridge.updateGitDecorations.connect(function (decorationsJson) {
      try {
        const decs = JSON.parse(decorationsJson);
        const mappedDecs = decs.map(d => {
          let className = '';
          if (d.type === 'added') className = 'git-gutter-added';
          else if (d.type === 'modified') className = 'git-gutter-modified';
          else if (d.type === 'deleted') className = 'git-gutter-deleted';
          
          return {
            range: new monaco.Range(d.start, 1, d.end || d.start, 1),
            options: {
              isWholeLine: false,
              linesDecorationsClassName: className
            }
          };
        });
        gitDecorations.set(mappedDecs);
      } catch (e) {
        console.error("Failed to parse git decorations", e);
      }
    });

    // Let Python know we are ready
    window.pythonBridge.onEditorReady();
  });
}

// Inject CSS for Git Gutters
const style = document.createElement('style');
style.innerHTML = `
  .git-gutter-added { border-left: 3px solid #2ea043; margin-left: 5px; }
  .git-gutter-modified { border-left: 3px solid #d29922; margin-left: 5px; }
  .git-gutter-deleted { 
    width: 0;
    height: 0;
    border-top: 4px solid transparent;
    border-left: 5px solid #f85149;
    border-bottom: 4px solid transparent;
    margin-left: 4px;
    transform: translateY(5px);
  }
`;
document.head.appendChild(style);

// Global accessor for debug/testing
window.editor = editor;
