apikey=$(shell cat APIKEY)

game_list.out: game_list.html APIKEY
	sed "s/\<GET_YOUR_OWN_API_KEY\>/${apikey}/" < game_list.html > game_list.out

clean:
	rm -f game_list.out
