var gulp = require('gulp');
var concat = require('gulp-concat');
var minify = require('gulp-minify');

gulp.task('default', function() {
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
});
