var gulp = require('gulp');
var concat = require('gulp-concat');
var minify = require('gulp-minify');
var sass = require('gulp-sass');
var clean_css = require('gulp-clean-css');
var rename = require('gulp-rename');
var argv = require('yargs').argv;

gulp.task('default', function() {
    // Build JS files
    gulp.src(['node_modules/jquery/dist/jquery.js',
              'node_modules/what-input/dist/what-input.js',
              'node_modules/foundation-sites/dist/foundation.js',
              'node_modules/foundation-datepicker/js/foundation-datepicker.js',
              'node_modules/jquery-ui/ui/version.js',
              'node_modules/jquery-ui/ui/data.js',
              'node_modules/jquery-ui/ui/scroll-parent.js',
              'node_modules/jquery-ui/ui/plugin.js',
              'node_modules/jquery-ui/ui/widget.js',
              'node_modules/jquery-ui/ui/widgets/mouse.js',
              'node_modules/jquery-ui/ui/position.js',
              'node_modules/jquery-ui/ui/widgets/draggable.js',
              'node_modules/jquery-ui/ui/widgets/droppable.js',
              'node_modules/jquery-ui/ui/widgets/resizable.js',
              'node_modules/jquery-ui/ui/widgets/selectable.js',
              'node_modules/jquery-ui/ui/widgets/sortable.js',
              'node_modules/jquery-ui/ui/effect.js',
              'node_modules/jquery-ui/ui/effects/*.js',
              'src/js/*.js']).
        pipe(concat('libraries.js')).
        pipe(minify({
            ext: {
                src: '.js',
                min: '.min.js'
            }
        })).
        pipe(gulp.dest('src/wte/static/js'));
    // Copy CodeMirror scripts
    gulp.src(['node_modules/codemirror/lib/codemirror.js']).
        pipe(gulp.dest('src/wte/static/js/codemirror'));
    gulp.src(['node_modules/codemirror/addon/**/*.js',
              'node_modules/codemirror/mode/**/*.js'], {base: 'node_modules/codemirror'}).
        pipe(gulp.dest('src/wte/static/js/codemirror'));
    // Copy MathJax
    gulp.src(['node_modules/mathjax/config/**/*.*',
              'node_modules/mathjax/extensions/**/*.*',
              'node_modules/mathjax/fonts/**/*.*',
              'node_modules/mathjax/images/**/*.*',
              'node_modules/mathjax/jax/**/*.*',
              'node_modules/mathjax/localization/**/*.*',
              'node_modules/mathjax/MathJax.js'], {base: 'node_modules/mathjax'}).
        pipe(gulp.dest('src/wte/static/js/mathjax'));
    // Build CSS files (inserting the optional user-provided settings and overrides SCSS files)
    var css_sources = ['src/scss/base-settings.scss'];
    if(argv.settings) {
        css_sources.push(argv.settings);
    }
    css_sources.push('src/scss/foundation-loader.scss');
    css_sources.push('src/scss/application.scss');
    if(argv.overrides) {
        css_sources.push(argv.overrides);
    }
    gulp.src(css_sources, {base: 'src/scss'}).
        pipe(concat('application.scss')).
        pipe(sass({
            includePaths: ['node_modules/foundation-sites/scss',
                           'node_modules/foundation-datepicker/scss',
                           'node_modules/foundation-icons',
                           'node_modules/codemirror/lib']
        })).
        pipe(clean_css()).
        pipe(rename('application.min.css')).
        pipe(gulp.dest('src/wte/static/css'));
    // Copy Foundation Icon Fonts
    gulp.src(['node_modules/foundation-icons/*.eot',
              'node_modules/foundation-icons/**/*.svg',
              'node_modules/foundation-icons/*.ttf',
              'node_modules/foundation-icons/*.woff'], {base: 'node_modules/foundation-icons'}).
        pipe(gulp.dest('src/wte/static/css'));
});
