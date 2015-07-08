// ==UserScript==
// @name        3D Vision Live Download Button
// @namespace   http://darkstarsword.net
// @include     http://photos.3dvisionlive.com/*/image/*
// @version     1
// @grant       none
// ==/UserScript==

var image = document.URL.split("/")[5];
var bar = document.getElementById("ph-player-int-bg");
var div = document.createElement("div");
var a = document.createElement("a");
a.href = "http://api.photos.3dvisionlive.com/imagestore/" + image + "/nvidia./";
a.setAttribute("download", a.href);
a.target = "_blank";
div.style = "color: #ccc; top: -1px; height: 24px; line-height: 24px; text-align: center; padding-right: 10px; padding-left: 10px;  margin: 1px;   background: #4c9300; float: right; position: relative; opacity: 0.6; font-weight:bold; font-size: 8pt";
div.className = "ph-player-int-btn-embed fade";
div.appendChild(document.createTextNode("DOWNLOAD"));
a.appendChild(div);
bar.appendChild(a);