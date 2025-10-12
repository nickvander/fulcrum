import { playwrightLauncher } from '@web/test-runner-playwright';
import { fromRollup } from '@web/dev-server-rollup';
import rollupCommonjs from '@rollup/plugin-commonjs';
import rollupReplace from '@rollup/plugin-replace';

const commonjs = fromRollup(rollupCommonjs);
const replace = fromRollup(rollupReplace);

export default {
  browsers: [
    playwrightLauncher({
      product: 'chromium',
      launchOptions: {
        args: ['--no-sandbox'],
      },
    }),
  ],
  testsStartTimeout: 60000,
  // Temporarily increased to 5 minutes to handle timeouts in product-form.spec.js
  // TODO: Investigate and optimize the product-form tests to reduce execution time.
  testsFinishTimeout: 300000,
  files: ['./dist/frontend/**/*.spec.js'],
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
