import { playwrightLauncher } from '@web/test-runner-playwright';
import { fromRollup } from '@web/dev-server-rollup';
import rollupCommonjs from '@rollup/plugin-commonjs';
import rollupReplace from '@rollup/plugin-replace';

const commonjs = fromRollup(rollupCommonjs);
const replace = fromRollup(rollupReplace);

export default {
  browsers: [
    playwrightLauncher({ product: 'chromium' }),
  ],
  testsStartTimeout: 60000,
  testFramework: {
    // we are using jasmine, so we don't need to configure anything here
  },
  plugins: [
    commonjs({
      include: ['**/node_modules/rxjs/**/*'],
    }),
    replace({
      preventAssignment: true,
      values: {
        'process.env.NODE_ENV': JSON.stringify('production'),
      },
    }),
  ],
};
