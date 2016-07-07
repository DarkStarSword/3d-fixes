var screenshot_width = 470;
var screenshot_height = 289;
var distance_multiplier = 0.80;
var current_screenshot_list = [];
var current_screenshot_table;
var current_screenshot_cols;
var current_screenshot_row;
var view_mode_html_fn;

function add_screenshot_to_table(id)
{
	if (current_screenshot_row.childNodes.length == current_screenshot_cols) {
		current_screenshot_row = document.createElement('tr');
		current_screenshot_table.appendChild(current_screenshot_row);
	}
	cell = document.createElement('td');
	cell.innerHTML = view_mode_html_fn(id);
	current_screenshot_row.appendChild(cell);
}

function create_screenshot_table(container, screenshot_list)
{
	container.innerHTML = "";
	current_screenshot_table = document.createElement('table');
	current_screenshot_table.style = 'margin-left: auto; margin-right: auto;';
	current_screenshot_row = document.createElement('tr');
	current_screenshot_table.appendChild(current_screenshot_row);
	for (var i in screenshot_list)
		add_screenshot_to_table(screenshot_list[i]);
	container.appendChild(current_screenshot_table);
}

function create_current_screenshot_table(container, screenshot_list)
{
	var containers = document.getElementsByClassName('screenshot_block');
	create_screenshot_table(containers[containers.length - 1], screenshot_lists[containers.length - 1]);
}

function update_all_screenshot_blocks(html_fn, cols)
{
	current_screenshot_cols = cols;
	view_mode_html_fn = html_fn;
	var containers = document.getElementsByClassName('screenshot_block');
	for (var i = 0; i < containers.length; i++)
		create_screenshot_table(containers[i], screenshot_lists[i]);
}

function save_view_mode(mode)
{
	var d = new Date();
	d.setTime(d.getTime() + 30*24*60*60*1000);
	document.cookie = 'screenshot_view_mode=' + mode + '; expires=' + d.toGMTString() + '; path=/';
}

function view_mode_plugin()
{
	save_view_mode('plugin');
	update_all_screenshot_blocks(function(id) {
		return '<iframe src="http://photos.3dvisionlive.com/e/embed/' + id + '/nvidia/' + screenshot_width + '.' + screenshot_height + '/important" width="' + screenshot_width + '" height="' + screenshot_height + '" frameborder="1" vspace="0" hspace="0" marginwidth="0" marginheight="0" scrolling="no" noresize><p>See stereo 3D on  <a href="http://photos.3dvisionlive.com">photos.3dvisionlive.com</a></p></iframe>';
	}, 2);
}

function view_mode_crosseyed()
{
	save_view_mode('crosseyed');
	update_all_screenshot_blocks(function(id) {
		return '<img src="http://api.photos.3dvisionlive.com/imagestore/' + id + '/nvidia./' + screenshot_width + '.' + screenshot_height + '/">';
	}, 1);
}

function reverse_eyes(img, id)
{
	var canvas = document.getElementById('canvas_' + id);
	var ctx = canvas.getContext('2d');
	var w = img.naturalWidth / 2;
	var h = img.naturalHeight;
	canvas.width = w * 2;
	canvas.height = h;

	ctx.drawImage(img, w, 0, w, h, 0, 0, w, h);
	ctx.drawImage(img, 0, 0, w, h, w, 0, w, h);
}

function view_mode_distance()
{
	save_view_mode('distance');
	update_all_screenshot_blocks(function(id) {
		var img = new Image();
		img.onload = function() { reverse_eyes(this, id) };
		img.id = 'screenshot_' + id;
		var ratio = screenshot_width / screenshot_height * distance_multiplier;
		img.src = 'http://api.photos.3dvisionlive.com/imagestore/' + id + '/nvidia./' + screenshot_width * distance_multiplier + '.' + screenshot_height * ratio + '/';
		return '<div><canvas id="canvas_' + id + '"></canvas></div>';
	}, 1);
}

function view_mode_anaglyph()
{
	save_view_mode('anaglyph');
	update_all_screenshot_blocks(function(id) {
		return '<img src="http://api.photos.3dvisionlive.com/imagestore/' + id + '/anaglyph./' + screenshot_width + '.' + screenshot_height + '/">';
	} , 2);
}

function restore_view_mode() {
	view_mode = document.cookie.match(new RegExp('(^| )screenshot_view_mode=([^;]+)'));
	if (view_mode == null)
		return view_mode_crosseyed();
	switch (view_mode[2]) {
	case 'plugin':
		view_mode_plugin();
		break;
	case 'distance':
		view_mode_distance();
		break;
	case 'anaglyph':
		view_mode_anaglyph();
		break;
	default:
		view_mode_crosseyed();
	}
}

function new_screenshot_block()
{
	document.write('<div class="screenshot_block"></div>');
	current_screenshot_list = [];
	screenshot_lists.push(current_screenshot_list);
	create_current_screenshot_table();
}

function embed_3dvisionlive(id)
{
	current_screenshot_list.push(id);
	add_screenshot_to_table(id);
}

document.write('<p style="text-align: center;">Select viewing method: <a href="javascript:view_mode_plugin();">3D Vision Plugin</a> - <a href="javascript:view_mode_crosseyed();">Cross-eyed</a> - <a href="javascript:view_mode_distance();">Distance</a> - <a href="javascript:view_mode_anaglyph();">Anaglyph</a></p>');

// Check if the script has been called already on this page (blog front page shows multiple posts)
if (typeof screenshot_lists === 'undefined') {
	document.write('<div class="screenshot_block"></div>');
	var screenshot_lists = [current_screenshot_list];
	restore_view_mode();
} else {
	new_screenshot_block();
}
