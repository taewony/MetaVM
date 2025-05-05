import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { IEditorTracker } from '@jupyterlab/fileeditor';

/**
 * 초기 확장 등록
 */
const extension: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab-meta-vm-extension:plugin',
  autoStart: true,
  requires: [IEditorTracker],
  activate: (app: JupyterFrontEnd, tracker: IEditorTracker) => {
    console.log('MetaVM IR extension activated');

    app.commands.addCommand('metavm:show-ir', {
      label: 'Show IR Text',
      execute: () => {
        const current = tracker.currentWidget;
        if (current) {
          const text = current.content.model?.sharedModel.getSource() ?? '';
          console.log('Current editor text:', text);
          // 여기에 IR 변환/뷰어 연동 추가 가능
        } else {
          console.warn('No active editor found.');
        }
      }
    });

    // JupyterLab 실행 시 자동 실행
    app.commands.execute('metavm:show-ir');
  }
};

export default extension;

