-- script.lua
-- Receives a table, returns the sum of its components.
-- io.write("The table the script received has:\n");
 x = ""
 pos = nil
 pos1 = nil
 defpos = nil
 lastdefpos = nil
 dclpos = nil
 lastdclpos = nil
 c7pos = nil
 lastc7pos = nil
 rpos = nil
 xpos = nil
 sr = ""
 sx = ""
 sw = ""
 isDone = false
 doSearch = true
 AddNextStr = true
 IsFirst = true
 ScreenToLS = nil
 SceneColorTexture = nil
 SamplerPos = nil
 SamplerName = ""
 MulEnd = nil
 rposEnd = nil;
 LightAttenuationTexture = nil
 textcordpos = nil
 textcordreg = ""
 FixSceneColorTexture = true
 FixShadowsHalo = nil
 UniformPixelVector = nil
 MinZ_MaxZRatio = nil
 ShadowTexture = nil
 VPreg = ""
 VPPos = nil
 LstIdx = 0;
 LightMapTextures = nil
 UniformPixelScalars = nil
 ScreenPositionScaleBias = nil
 Texture2D_2 = nil
 -- search for constants names it helps to determinate shader 
 for i = 1, #SText do
	if pos == nil then
		pos = string.find(SText[i], "bReceiveDynamicShadows")
	end

	if pos1 == nil then
		pos1 = string.find(SText[i], "ViewProjectionMatrix")
		LstIdx = i + 1
	end
	
	if LightAttenuationTexture == nil then
		LightAttenuationTexture = string.find(SText[i], "LightAttenuationTexture")
	end
	
	if LightMapTextures == nil then
		LightMapTextures = string.find(SText[i], "LightMapTextures")
		if LightMapTextures ~= nil then
			LightMapTextures = i
		end
	end
	
	if UniformPixelScalars == nil then
		UniformPixelScalars = string.find(SText[i], "UniformPixelScalars")
	end
	
	if ScreenPositionScaleBias == nil then
		ScreenPositionScaleBias = string.find(SText[i], "ScreenPositionScaleBias")
	end
	
	if Texture2D_2 == nil then
		Texture2D_2 = string.find(SText[i], "Texture2D_2")
	end
	
	
	
	if SceneColorTexture == nil then
		SceneColorTexture = string.find(SText[i], "SceneColorTexture")
		if SceneColorTexture ~= nil then
			SceneColorTexture = i
		end
	end

	if ScreenToLS == nil then
		ScreenToLS = string.find(SText[i], "ScreenToLight")
	end
	
	if ShadowTexture == nil then
		ShadowTexture = string.find(SText[i], "ShadowTexture")
	end
	
	
	
	if ScreenToLS == nil then
		ScreenToLS = string.find(SText[i], "ScreenToShadowMatrix")
	end
	
	if UniformPixelVector == nil then
		UniformPixelVector = string.find(SText[i], "UniformPixelVector")
	end
	
	if MinZ_MaxZRatio == nil then
		MinZ_MaxZRatio = string.find(SText[i], "MinZ_MaxZRatio")
	end
	
	
	--x = x .. SText[i] .. string.char(13)
	if string.find(SText[i], "ps_3_0") ~= nil then
		break
	end
 end

 if isDone == false then
--and (MinZ_MaxZRatio ~= nil) 
if (SceneColorTexture ~= nil) then
	StartIdx = SceneColorTexture
else
	StartIdx = LightMapTextures
end
if (((SceneColorTexture ~= nil) or (LightMapTextures ~= nil)) and (UniformPixelVector ~= nil) and (ScreenToLS == nil) and (ShadowTexture == nil)) or ((SceneColorTexture ~= nil) and (UniformPixelScalars ~= nil) and (ScreenPositionScaleBias ~= nil) and (Texture2D_2 ~= nil) and (UniformPixelVector == nil)) and FixSceneColorTexture then 
	for i = StartIdx + 1, #SText do
		AddNextStr = true
		--if doSearch then
			if SamplerPos == nil then
				if (SceneColorTexture ~= nil) then
					SamplerPos = string.find(SText[i], "SceneColorTexture")
				else
					SamplerPos = string.find(SText[i], "LightMapTextures")
				end
				
			end
			

			
			if SamplerPos ~= nil then
			    if SamplerName == "" then
					SamplerPos = string.find(SText[i], "s", SamplerPos + 16)
					SamplerName = string.sub(SText[i], SamplerPos, SamplerPos + 1)
				end
				if SamplerName ~= "" then
				
					lastdefpos = string.find(SText[i], "def")
					if lastdefpos ~= nil then
						defpos = i + 1
					end
	
					if (lastdefpos == nil) and (defpos ~= nil) then
						if i == defpos then
							x = x .. "   def c200, 0.0, 0.5, 0.0625, 0 " .. string.char(10)	
						end
						lastdclpos = string.find(SText[i], "dcl_2")
			
						if lastdclpos == nil then
							lastdclpos = string.find(SText[i], "dcl_cube")
						end
			
						if lastdclpos ~= nil then
							dclpos = i + 1
						end
		
						if (lastdclpos == nil) and (dclpos ~= nil) then
							if i == dclpos then
								x = x .. "   dcl_2d s15" .. string.char(10)	
							end			
						end
					end
				end
			end
			
			if FixSceneColorTexture then
				if textcordreg ~= "" then
				isDone = true
					rpos, rposEnd = string.find(SText[i], textcordreg)
					if rpos ~= nil then
					
						if IsFirst then
							x = x .. "    mov r16.xyw, " .. textcordreg .. string.char(10)			
							x = x .. "    texldl r11, c200.z, s15" .. string.char(10)
							x = x .. "    add r11.y, r16.w, -r11.y" .. string.char(10)
							x = x .. "    mul r11.x, r11.x, r11.y" .. string.char(10)
							x = x .. "    add r16.x, r16.x, r11.x" .. string.char(10)
							--doSearch = false
							isDone = true
									
						end
						IsFirst = false;
						str = string.sub(SText[i], 1, rpos - 1) 
						str = str .. "r16" .. string.sub(SText[i], rposEnd + 1) 
						SText[i] = str				
					end
				end
				
				if textcordpos == nil then
					textcordpos, rposEnd = string.find(SText[i], "dcl_texcoord5 v")
					if textcordpos ~= nil then
						textcordpos = string.find(SText[i], "." ,rposEnd - 1, true)
						textcordreg = string.sub(SText[i], rposEnd - 1, textcordpos - 1) 
					end
				end
			end
		--end
		if AddNextStr then
			x = x .. SText[i] .. string.char(10)
		end	
	end
end
end

if isDone == false then
-- it's probably dynamic shadows/lights
-- will try to inject out fixing code after retriving value from W buffer
if (SceneColorTexture ~= nil) and (ScreenToLS ~= nil) then
	for i = SceneColorTexture + 1, #SText do
		AddNextStr = true
		if doSearch then
			if SamplerPos == nil then
				SamplerPos = string.find(SText[i], "SceneColorTexture")
			end
			

			
			if SamplerPos ~= nil then
			    if SamplerName == "" then
					SamplerPos = string.find(SText[i], "s", SamplerPos + 16)
					SamplerName = string.sub(SText[i], SamplerPos, SamplerPos + 1)
				end
				if SamplerName ~= "" then
				
					lastdefpos = string.find(SText[i], "def")
					if lastdefpos ~= nil then
						defpos = i + 1
					end
	
					if (lastdefpos == nil) and (defpos ~= nil) then
						if i == defpos then
							x = x .. "   def c200, 0.0, 0.5, 0.0625, 0 " .. string.char(10)	
						end
						lastdclpos = string.find(SText[i], "dcl_2")
			
						if lastdclpos == nil then
							lastdclpos = string.find(SText[i], "dcl_cube")
						end
			
						if lastdclpos ~= nil then
							dclpos = i + 1
						end
		
						if (lastdclpos == nil) and (dclpos ~= nil) then
							if i == dclpos then
								x = x .. "   dcl_2d s15" .. string.char(10)	
							end
							
							if c7pos == nil then
								c7pos = string.find(SText[i], SamplerName)
							
								if c7pos ~= nil then
									c7pos = string.find(SText[i], "texld")
									if c7pos ~= nil then	
										if MinZ_MaxZRatio ~= nil then
											c7pos = i + 6
										else
											c7pos = i + 2
										end
									end
								end
							end
							if c7pos == i then	
								rpos, MulEnd = string.find(SText[c7pos], "mul ")
								if rpos == nil then
									rpos, MulEnd = string.find(SText[c7pos], "mul_pp ")
								end
								if rpos ~= nil then
									--rpos = rpos + 4
									xpos = string.find(SText[c7pos], ".", MulEnd, true)
									sr = string.sub(SText[c7pos], MulEnd, xpos  - 1)
									sx = string.sub(SText[c7pos], xpos + 1, xpos + 1)
									
									xpos, rposEnd = string.find(SText[c7pos], sr, xpos + 1)
									
									
									sw = string.sub(SText[c7pos], rposEnd + 2, rposEnd + 2)
						
									x = x .. SText[i] .. string.char(10)
									x = x .. "    texldl r11, c200.z, s15" .. string.char(10)
									x = x .. "    add r11.y, " .. sr .. "." .. sw .. ", -r11.y" .. string.char(10)
									x = x .. "    mul r11.x, r11.x, r11.y" .. string.char(10)
									x = x .. "    add " .. sr .. "." .. sx .. ", " .. sr .. "." .. sx .. ", -r11.x" .. string.char(10)
									doSearch = false
									isDone = true
									AddNextStr = false
								end
							end
						end
					end
				end
			end
			
			if FixSceneColorTexture then
				if textcordreg ~= "" then
					rpos, rposEnd = string.find(SText[i], textcordreg)
					if rpos ~= nil then
					
						if IsFirst then
							x = x .. "    mov r16.xyw, " .. textcordreg .. string.char(10)			
							x = x .. "    texldl r11, c200.z, s15" .. string.char(10)
							x = x .. "    add r11.y, r16.w, -r11.y" .. string.char(10)
							x = x .. "    mul r11.x, r11.x, r11.y" .. string.char(10)
							x = x .. "    add r16.x, r16.x, r11.x" .. string.char(10)
						end
						IsFirst = false;
						str = string.sub(SText[i], 1, rpos - 1) 
						str = str .. "r16" .. string.sub(SText[i], rposEnd + 1) 
						isDone = true
						SText[i] = str				
					end
				end
				
				if textcordpos == nil then
					textcordpos, rposEnd = string.find(SText[i], "dcl_texcoord v")
					if textcordpos ~= nil then
						textcordpos = string.find(SText[i], "." ,rposEnd - 1, true)
						textcordreg = string.sub(SText[i], rposEnd - 1, textcordpos - 1) 
					end
				end
			end
		end
		if AddNextStr then
			x = x .. SText[i] .. string.char(10)
		end	
	end
end
end

if isDone == false then
-- probably static/world shadows, inject code by a template
if ((pos ~= nil) or (ShadowTexture and  SceneColorTexture)) and (pos1 ~= nil) then 
 isDone = true
 for i = LstIdx + 1, #SText do
    AddNextStr = true
	if doSearch then
 
		if VPPos == nil then
			VPPos = string.find(SText[i], "ViewProjectionMatrix")
			if(VPPos ~= nil) then
				xpos = string.find(SText[i], "c", VPPos + 19, true)
				
				if(xpos ~= nil) then
					--VPPos = string.find(SText[i], " ", xpos, true)
					VPreg = string.sub(SText[i], xpos, xpos + 1)
					--x = x .." //" ..VPreg .. string.char(10)
					
				end
				
			end
		end
		lastdefpos = string.find(SText[i], "def")
		if lastdefpos ~= nil then
			defpos = i + 1
		end
	
		if (lastdefpos == nil) and (defpos ~= nil) then
			if i == defpos then
				x = x .. "   def c200, 0.0, 0.5, 0.0625, 0" .. string.char(10)	
			end
			lastdclpos = string.find(SText[i], "dcl_2")
			
			if lastdclpos == nil then
				lastdclpos = string.find(SText[i], "dcl_cube")
			end
			
			if lastdclpos ~= nil then
			dclpos = i + 1
			end
		
			if (lastdclpos == nil) and (dclpos ~= nil) and (VPreg ~= "") then
				if i == dclpos then
					x = x .. "   dcl_2d s15" .. string.char(10)	
				end
				c7pos = string.find(SText[i], VPreg)
				if c7pos ~= nil then
					c7pos = i + 2;
					rpos = string.find(SText[i], "mad ")
					if rpos ~= nil then
						rpos = rpos + 4
						xpos = string.find(SText[i], ".", rpos, true)

						sr = string.sub(SText[i], rpos, xpos - 1)
						sx = string.sub(SText[i], xpos + 1, xpos + 1)
						sw = string.sub(SText[i], xpos + 3, xpos + 3)
						x = x .. SText[i] .. string.char(10)
						x = x .. SText[i + 1] .. string.char(10)
						x = x .. SText[i + 2] .. string.char(10)
						SText[i + 1] = ""
						SText[i + 2] = ""
						x = x .. "    texldl r11, c200.z, s15" .. string.char(10)
						x = x .. "    add r11.y, " .. sr .. "." .. sw .. ", -r11.y" .. string.char(10)
						x = x .. "    mul r11.x, r11.x, r11.y" .. string.char(10)
						x = x .. "    add " .. sr .. "." .. sx .. ", " .. sr .. "." .. sx .. ", r11.x" .. string.char(10)
						doSearch = false
						isDone = true
						AddNextStr = false
					end
				
				end
			end
		end
	end
	if AddNextStr then
		x = x .. SText[i] .. string.char(10)
	end
end
end
end

if isDone == false then
-- or ((SceneColorTexture ~= nil) and (ShadowTexture ~= nil) and (UniformPixelVector ~= nil)
if (pos ~= nil) and (LightAttenuationTexture ~= nil) and (pos1 == nil)  then 
 
 for i = 1, #SText do
    AddNextStr = true
	if doSearch then
 
		lastdefpos = string.find(SText[i], "def")
		if lastdefpos ~= nil then
			defpos = i + 1
		end
		
		
		if textcordpos == nil then
			textcordpos, rposEnd = string.find(SText[i], "dcl_texcoord7 ")
			if textcordpos ~= nil then
			    textcordpos = string.find(SText[i], "." ,rposEnd, true)
				textcordreg = string.sub(SText[i], rposEnd, textcordpos - 1) 
			end
			--defpos = i + 1
		end
	
		if (lastdefpos == nil) and (defpos ~= nil) then
			if i == defpos then
				x = x .. "   def c200, 0.0, 0.5, 0.0625, 0" .. string.char(10)	
			end
			lastdclpos = string.find(SText[i], "dcl_2")
			
			if lastdclpos == nil then
				lastdclpos = string.find(SText[i], "dcl_cube")
			end
			
			if lastdclpos ~= nil then
			dclpos = i + 1
			end
		
			if (lastdclpos == nil) and (dclpos ~= nil) then
				if i == dclpos then
					x = x .. "   dcl_2d s15" .. string.char(10)	
				end
				c7pos, rposEnd = string.find(SText[i], textcordreg)
				if c7pos ~= nil then
					
					if IsFirst then
						x = x .. "    mov r16.xyw, " .. textcordreg .. string.char(10)
			
						x = x .. "    texldl r11, c200.z, s15" .. string.char(10)
						x = x .. "    add r11.y, r16.w, -r11.y" .. string.char(10)
						x = x .. "    mul r11.x, r11.x, r11.y" .. string.char(10)
						x = x .. "    add r16.x, r16.x, r11.x" .. string.char(10)
					end
					IsFirst = false;
					str = string.sub(SText[i], 1, c7pos - 1) 
					str = str .. "r16" .. string.sub(SText[i], rposEnd + 1) 
					SText[i] = str
						--doSearch = false
					isDone = true
						--AddNextStr = false
					
				
				end
			end
		end
	end
	if AddNextStr then
		x = x .. SText[i] .. string.char(10)
	end
end
end
end

if isDone then
	return x
else
	return ""
end;
