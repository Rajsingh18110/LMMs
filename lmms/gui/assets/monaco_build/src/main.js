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
import getChatServiceOverride from '@codingame/monaco-vscode-chat-service-override';
import getViewsServiceOverride from '@codingame/monaco-vscode-views-service-override';
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
    'editor.background':                '#1e1e1e',
    'editor.foreground':                '#d4d4d4',
    'editorLineNumber.foreground':      '#858585',
    'editorLineNumber.activeForeground':'#c6c6c6',
    'editorCursor.foreground':          '#aeafad',
    'editor.selectionBackground':       '#264f78',
    'editor.inactiveSelectionBackground':'#3a3d41',
    'editor.lineHighlightBackground':   '#2a2a2a',
    'editor.lineHighlightBorder':       '#00000000',
    'editorGutter.background':          '#1e1e1e',
    'editorWidget.background':          '#252526',
    'editorWidget.border':              '#454545',
    'editorSuggestWidget.background':   '#252526',
    'editorSuggestWidget.border':       '#454545',
    'editorSuggestWidget.selectedBackground': '#062f4a',
    'editorHoverWidget.background':     '#252526',
    'editorHoverWidget.border':         '#454545',
    'editorIndentGuide.background1':    '#404040',
    'editorIndentGuide.activeBackground1': '#707070',
    'scrollbarSlider.background':       '#424242',
    'scrollbarSlider.hoverBackground':  '#4f4f4f',
    'scrollbarSlider.activeBackground': '#646464',
  }
});

import 'vscode/localExtensionHost';
import { registerExtension, ExtensionHostKind } from 'vscode/extensions';

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
  ...getChatServiceOverride(),
  ...getViewsServiceOverride(),
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
  glyphMargin: true,
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
        this.bridge.sendLspMessage.connect(handler);
        return { dispose: () => this.bridge.sendLspMessage.disconnect(handler) };
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
            this.bridge.onLspMessage(JSON.stringify(msg));
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
    
    // Send cursor position changes
    editor.onDidChangeCursorPosition((e) => {
      if (window.pythonBridge.onCursorPositionChanged) {
        window.pythonBridge.onCursorPositionChanged(e.position.lineNumber, e.position.column);
      }
    });
    
    // Listen for jumpTo requests
    window.pythonBridge.jumpTo.connect(function (line, col) {
      editor.setPosition({ lineNumber: line + 1, column: col + 1 });
      editor.revealLineInCenter(line + 1);
      editor.focus();
    });
    
    // Listen for Breakpoint clicks
    let breakpointDecorations = editor.createDecorationsCollection();
    let currentBreakpoints = [];
    
    editor.onMouseDown(function (e) {
      if (e.target.type === monaco.editor.MouseTargetType.GUTTER_GLYPH_MARGIN) {
        const line = e.target.position.lineNumber;
        
        // Toggle breakpoint
        const idx = currentBreakpoints.indexOf(line);
        if (idx !== -1) {
          currentBreakpoints.splice(idx, 1);
        } else {
          currentBreakpoints.push(line);
        }
        
        // Redraw
        const newDecorations = currentBreakpoints.map(l => ({
          range: new monaco.Range(l, 1, l, 1),
          options: {
            isWholeLine: false,
            glyphMarginClassName: 'dap-breakpoint-glyph',
            glyphMarginHoverMessage: { value: 'Breakpoint' }
          }
        }));
        breakpointDecorations.set(newDecorations);
        
        // Notify Python
        if (window.pythonBridge.toggleBreakpoint) {
          window.pythonBridge.toggleBreakpoint(line - 1); // 0-indexed for Python
        }
      }
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
    
    // Register Extension (from Python)
    if (window.pythonBridge.registerExtension) {
      window.pythonBridge.registerExtension.connect(async function(manifestJson) {
        try {
          const manifest = JSON.parse(manifestJson);
          const extensionLocation = manifest.extensionLocation || '';
          // We use WebWorker or LocalProcess. If LocalProcess, it tells Monaco it's running outside.
          const { registerFileUrl, getApi } = registerExtension(manifest, ExtensionHostKind.LocalProcess);
          
          if (extensionLocation) {
             // In a full implementation, you would map paths via registerFileUrl
             console.log(`Registered extension: ${manifest.name} at ${extensionLocation}`);
          }
          
          const api = await getApi();
          // Activation logic is often handled by Monaco internally when an activationEvent occurs, 
          // but we can manually trigger activate if needed.
          // Note: LocalProcess expects the actual code to run in Node.js (runner.js) which we still spawn.
          console.log(`Extension API ready for ${manifest.name}`);
        } catch (err) {
          console.error("Failed to register extension", err);
        }
      });
    }
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
