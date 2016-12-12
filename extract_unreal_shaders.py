#!/usr/bin/env python3

from extract_unity_shaders import fnv_3Dmigoto_shader
from extract_unity_shaders import export_dx11_shader
from extract_unity_shaders import add_vanity_tag
from extract_unity_shaders import commentify
import sys, os, struct, argparse, codecs, hashlib, io, textwrap

verbosity = 0

def pr_debug(*msg, **kwargs):
	if verbosity:
		print(*msg, **kwargs)

headers = None

def start_headers():
	global headers
	headers = io.StringIO()

def end_headers():
	global headers
	ret = headers.getvalue().splitlines(True)
	add_vanity_tag(ret)
	headers = None
	return commentify(ret)

def pr_headers(*msg, **kwargs):
	global headers
	if headers is not None:
		print(*msg, file=headers, **kwargs)
	pr_debug(*msg, **kwargs)

class VER_UE4(object):
	OLDEST_LOADABLE_PACKAGE = 214
	BLUEPRINT_VARS_NOT_READ_ONLY = 215
	STATIC_MESH_STORE_NAV_COLLISION = 216
	ATMOSPHERIC_FOG_DECAY_NAME_CHANGE = 217
	SCENECOMP_TRANSLATION_TO_LOCATION = 218
	MATERIAL_ATTRIBUTES_REORDERING = 219
	COLLISION_PROFILE_SETTING = 220
	BLUEPRINT_SKEL_TEMPORARY_TRANSIENT = 221
	BLUEPRINT_SKEL_SERIALIZED_AGAIN = 222
	BLUEPRINT_SETS_REPLICATION = 223
	WORLD_LEVEL_INFO = 224
	AFTER_CAPSULE_HALF_HEIGHT_CHANGE = 225
	ADDED_NAMESPACE_AND_KEY_DATA_TO_FTEXT = 226
	ATTENUATION_SHAPES = 227
	LIGHTCOMPONENT_USE_IES_TEXTURE_MULTIPLIER_ON_NON_IES_BRIGHTNESS = 228
	REMOVE_INPUT_COMPONENTS_FROM_BLUEPRINTS = 229
	VARK2NODE_USE_MEMBERREFSTRUCT = 230
	REFACTOR_MATERIAL_EXPRESSION_SCENECOLOR_AND_SCENEDEPTH_INPUTS = 231
	SPLINE_MESH_ORIENTATION = 232
	REVERB_EFFECT_ASSET_TYPE = 233
	MAX_TEXCOORD_INCREASED = 234
	SPEEDTREE_STATICMESH = 235
	LANDSCAPE_COMPONENT_LAZY_REFERENCES = 236
	SWITCH_CALL_NODE_TO_USE_MEMBER_REFERENCE = 237
	ADDED_SKELETON_ARCHIVER_REMOVAL = 238
	ADDED_SKELETON_ARCHIVER_REMOVAL_SECOND_TIME = 239
	BLUEPRINT_SKEL_CLASS_TRANSIENT_AGAIN = 240
	ADD_COOKED_TO_UCLASS = 241
	DEPRECATED_STATIC_MESH_THUMBNAIL_PROPERTIES_REMOVED = 242
	COLLECTIONS_IN_SHADERMAPID = 243
	REFACTOR_MOVEMENT_COMPONENT_HIERARCHY = 244
	FIX_TERRAIN_LAYER_SWITCH_ORDER = 245
	ALL_PROPS_TO_CONSTRAINTINSTANCE = 246
	LOW_QUALITY_DIRECTIONAL_LIGHTMAPS = 247
	ADDED_NOISE_EMITTER_COMPONENT = 248
	ADD_TEXT_COMPONENT_VERTICAL_ALIGNMENT = 249
	ADDED_FBX_ASSET_IMPORT_DATA = 250
	REMOVE_LEVELBODYSETUP = 251
	REFACTOR_CHARACTER_CROUCH = 252
	SMALLER_DEBUG_MATERIALSHADER_UNIFORM_EXPRESSIONS = 253
	APEX_CLOTH = 254
	SAVE_COLLISIONRESPONSE_PER_CHANNEL = 255
	ADDED_LANDSCAPE_SPLINE_EDITOR_MESH = 256
	CHANGED_MATERIAL_REFACTION_TYPE = 257
	REFACTOR_PROJECTILE_MOVEMENT = 258
	REMOVE_PHYSICALMATERIALPROPERTY = 259
	PURGED_FMATERIAL_COMPILE_OUTPUTS = 260
	ADD_COOKED_TO_LANDSCAPE = 261
	CONSUME_INPUT_PER_BIND = 262
	SOUND_CLASS_GRAPH_EDITOR = 263
	FIXUP_TERRAIN_LAYER_NODES = 264
	RETROFIT_CLAMP_EXPRESSIONS_SWAP = 265
	REMOVE_LIGHT_MOBILITY_CLASSES = 266
	REFACTOR_PHYSICS_BLENDING = 267
	WORLD_LEVEL_INFO_UPDATED = 268
	STATIC_SKELETAL_MESH_SERIALIZATION_FIX = 269
	REMOVE_STATICMESH_MOBILITY_CLASSES = 270
	REFACTOR_PHYSICS_TRANSFORMS = 271
	REMOVE_ZERO_TRIANGLE_SECTIONS = 272
	CHARACTER_MOVEMENT_DECELERATION = 273
	CAMERA_ACTOR_USING_CAMERA_COMPONENT = 274
	CHARACTER_MOVEMENT_DEPRECATE_PITCH_ROLL = 275
	REBUILD_TEXTURE_STREAMING_DATA_ON_LOAD = 276
	SUPPORT_32BIT_STATIC_MESH_INDICES = 277
	ADDED_CHUNKID_TO_ASSETDATA_AND_UPACKAGE = 278
	CHARACTER_DEFAULT_MOVEMENT_BINDINGS = 279
	APEX_CLOTH_LOD = 280
	ATMOSPHERIC_FOG_CACHE_DATA = 281
	ARRAY_PROPERTY_INNER_TAGS = 282
	KEEP_SKEL_MESH_INDEX_DATA = 283
	BODYSETUP_COLLISION_CONVERSION = 284
	REFLECTION_CAPTURE_COOKING = 285
	REMOVE_DYNAMIC_VOLUME_CLASSES = 286
	STORE_HASCOOKEDDATA_FOR_BODYSETUP = 287
	REFRACTION_BIAS_TO_REFRACTION_DEPTH_BIAS = 288
	REMOVE_SKELETALPHYSICSACTOR = 289
	PC_ROTATION_INPUT_REFACTOR = 290
	LANDSCAPE_PLATFORMDATA_COOKING = 291
	CREATEEXPORTS_CLASS_LINKING_FOR_BLUEPRINTS = 292
	REMOVE_NATIVE_COMPONENTS_FROM_BLUEPRINT_SCS = 293
	REMOVE_SINGLENODEINSTANCE = 294
	CHARACTER_BRAKING_REFACTOR = 295
	VOLUME_SAMPLE_LOW_QUALITY_SUPPORT = 296
	SPLIT_TOUCH_AND_CLICK_ENABLES = 297
	HEALTH_DEATH_REFACTOR = 298
	SOUND_NODE_ENVELOPER_CURVE_CHANGE = 299
	POINT_LIGHT_SOURCE_RADIUS = 300
	SCENE_CAPTURE_CAMERA_CHANGE = 301
	MOVE_SKELETALMESH_SHADOWCASTING = 302
	CHANGE_SETARRAY_BYTECODE = 303
	MATERIAL_INSTANCE_BASE_PROPERTY_OVERRIDES = 304
	COMBINED_LIGHTMAP_TEXTURES = 305
	BUMPED_MATERIAL_EXPORT_GUIDS = 306
	BLUEPRINT_INPUT_BINDING_OVERRIDES = 307
	FIXUP_BODYSETUP_INVALID_CONVEX_TRANSFORM = 308
	FIXUP_STIFFNESS_AND_DAMPING_SCALE = 309
	REFERENCE_SKELETON_REFACTOR = 310
	K2NODE_REFERENCEGUIDS = 311
	FIXUP_ROOTBONE_PARENT = 312
	TEXT_RENDER_COMPONENTS_WORLD_SPACE_SIZING = 313
	MATERIAL_INSTANCE_BASE_PROPERTY_OVERRIDES_PHASE_2 = 314
	CLASS_NOTPLACEABLE_ADDED = 315
	WORLD_LEVEL_INFO_LOD_LIST = 316
	CHARACTER_MOVEMENT_VARIABLE_RENAMING_1 = 317
	FSLATESOUND_CONVERSION = 318
	WORLD_LEVEL_INFO_ZORDER = 319
	PACKAGE_REQUIRES_LOCALIZATION_GATHER_FLAGGING = 320
	BP_ACTOR_VARIABLE_DEFAULT_PREVENTING = 321
	TEST_ANIMCOMP_CHANGE = 322
	EDITORONLY_BLUEPRINTS = 323
	EDGRAPHPINTYPE_SERIALIZATION = 324
	NO_MIRROR_BRUSH_MODEL_COLLISION = 325
	CHANGED_CHUNKID_TO_BE_AN_ARRAY_OF_CHUNKIDS = 326
	WORLD_NAMED_AFTER_PACKAGE = 327
	SKY_LIGHT_COMPONENT = 328
	WORLD_LAYER_ENABLE_DISTANCE_STREAMING = 329
	REMOVE_ZONES_FROM_MODEL = 330
	FIX_ANIMATIONBASEPOSE_SERIALIZATION = 331
	SUPPORT_8_BONE_INFLUENCES_SKELETAL_MESHES = 332
	ADD_OVERRIDE_GRAVITY_FLAG = 333
	SUPPORT_GPUSKINNING_8_BONE_INFLUENCES = 334
	ANIM_SUPPORT_NONUNIFORM_SCALE_ANIMATION = 335
	ENGINE_VERSION_OBJECT = 336
	PUBLIC_WORLDS = 337
	SKELETON_GUID_SERIALIZATION = 338
	CHARACTER_MOVEMENT_WALKABLE_FLOOR_REFACTOR = 339
	INVERSE_SQUARED_LIGHTS_DEFAULT = 340
	DISABLED_SCRIPT_LIMIT_BYTECODE = 341
	PRIVATE_REMOTE_ROLE = 342
	FOLIAGE_STATIC_MOBILITY = 343
	BUILD_SCALE_VECTOR = 344
	FOLIAGE_COLLISION = 345
	SKY_BENT_NORMAL = 346
	LANDSCAPE_COLLISION_DATA_COOKING = 347
	MORPHTARGET_CPU_TANGENTZDELTA_FORMATCHANGE = 348
	SOFT_CONSTRAINTS_USE_MASS = 349
	REFLECTION_DATA_IN_PACKAGES = 350
	FOLIAGE_MOVABLE_MOBILITY = 351
	UNDO_BREAK_MATERIALATTRIBUTES_CHANGE = 352
	ADD_CUSTOMPROFILENAME_CHANGE = 353
	FLIP_MATERIAL_COORDS = 354
	MEMBERREFERENCE_IN_PINTYPE = 355
	VEHICLES_UNIT_CHANGE = 356
	ANIMATION_REMOVE_NANS = 357
	SKELETON_ASSET_PROPERTY_TYPE_CHANGE = 358
	FIX_BLUEPRINT_VARIABLE_FLAGS = 359
	VEHICLES_UNIT_CHANGE2 = 360
	UCLASS_SERIALIZE_INTERFACES_AFTER_LINKING = 361
	STATIC_MESH_SCREEN_SIZE_LODS = 362
	FIX_MATERIAL_COORDS = 363
	SPEEDTREE_WIND_V7 = 364
	LOAD_FOR_EDITOR_GAME = 365
	SERIALIZE_RICH_CURVE_KEY = 366
	MOVE_LANDSCAPE_MICS_AND_TEXTURES_WITHIN_LEVEL = 367
	FTEXT_HISTORY = 368
	FIX_MATERIAL_COMMENTS = 369
	STORE_BONE_EXPORT_NAMES = 370
	MESH_EMITTER_INITIAL_ORIENTATION_DISTRIBUTION = 371
	DISALLOW_FOLIAGE_ON_BLUEPRINTS = 372
	FIXUP_MOTOR_UNITS = 373
	DEPRECATED_MOVEMENTCOMPONENT_MODIFIED_SPEEDS = 374
	RENAME_CANBECHARACTERBASE = 375
	GAMEPLAY_TAG_CONTAINER_TAG_TYPE_CHANGE = 376
	FOLIAGE_SETTINGS_TYPE = 377
	STATIC_SHADOW_DEPTH_MAPS = 378
	ADD_TRANSACTIONAL_TO_DATA_ASSETS = 379
	ADD_LB_WEIGHTBLEND = 380
	ADD_ROOTCOMPONENT_TO_FOLIAGEACTOR = 381
	FIX_MATERIAL_PROPERTY_OVERRIDE_SERIALIZE = 382
	ADD_LINEAR_COLOR_SAMPLER = 383
	ADD_STRING_ASSET_REFERENCES_MAP = 384
	BLUEPRINT_USE_SCS_ROOTCOMPONENT_SCALE = 385
	LEVEL_STREAMING_DRAW_COLOR_TYPE_CHANGE = 386
	CLEAR_NOTIFY_TRIGGERS = 387
	SKELETON_ADD_SMARTNAMES = 388
	ADDED_CURRENCY_CODE_TO_FTEXT = 389
	ENUM_CLASS_SUPPORT = 390
	FIXUP_WIDGET_ANIMATION_CLASS = 391
	SOUND_COMPRESSION_TYPE_ADDED = 392
	AUTO_WELDING = 393
	RENAME_CROUCHMOVESCHARACTERDOWN = 394
	LIGHTMAP_MESH_BUILD_SETTINGS = 395
	RENAME_SM3_TO_ES3_1 = 396
	DEPRECATE_UMG_STYLE_ASSETS = 397
	POST_DUPLICATE_NODE_GUID = 398
	RENAME_CAMERA_COMPONENT_VIEW_ROTATION = 399
	CASE_PRESERVING_FNAME = 400
	RENAME_CAMERA_COMPONENT_CONTROL_ROTATION = 401
	FIX_REFRACTION_INPUT_MASKING = 402
	GLOBAL_EMITTER_SPAWN_RATE_SCALE = 403
	CLEAN_DESTRUCTIBLE_SETTINGS = 404
	CHARACTER_MOVEMENT_UPPER_IMPACT_BEHAVIOR = 405
	BP_MATH_VECTOR_EQUALITY_USES_EPSILON = 406
	FOLIAGE_STATIC_LIGHTING_SUPPORT = 407
	SLATE_COMPOSITE_FONTS = 408
	REMOVE_SAVEGAMESUMMARY = 409
	REMOVE_SKELETALMESH_COMPONENT_BODYSETUP_SERIALIZATION = 410
	SLATE_BULK_FONT_DATA = 411
	ADD_PROJECTILE_FRICTION_BEHAVIOR = 412
	MOVEMENTCOMPONENT_AXIS_SETTINGS = 413
	GRAPH_INTERACTIVE_COMMENTBUBBLES = 414
	LANDSCAPE_SERIALIZE_PHYSICS_MATERIALS = 415
	RENAME_WIDGET_VISIBILITY = 416
	ANIMATION_ADD_TRACKCURVES = 417
	MONTAGE_BRANCHING_POINT_REMOVAL = 418
	BLUEPRINT_ENFORCE_CONST_IN_FUNCTION_OVERRIDES = 419
	ADD_PIVOT_TO_WIDGET_COMPONENT = 420
	PAWN_AUTO_POSSESS_AI = 421
	FTEXT_HISTORY_DATE_TIMEZONE = 422
	SORT_ACTIVE_BONE_INDICES = 423
	PERFRAME_MATERIAL_UNIFORM_EXPRESSIONS = 424
	MIKKTSPACE_IS_DEFAULT = 425
	LANDSCAPE_GRASS_COOKING = 426
	FIX_SKEL_VERT_ORIENT_MESH_PARTICLES = 427
	LANDSCAPE_STATIC_SECTION_OFFSET = 428
	ADD_MODIFIERS_RUNTIME_GENERATION = 429
	MATERIAL_MASKED_BLENDMODE_TIDY = 430
	MERGED_ADD_MODIFIERS_RUNTIME_GENERATION_TO_4_7_DEPRECATED = 431
	AFTER_MERGED_ADD_MODIFIERS_RUNTIME_GENERATION_TO_4_7_DEPRECATED = 432
	MERGED_ADD_MODIFIERS_RUNTIME_GENERATION_TO_4_7 = 433
	AFTER_MERGING_ADD_MODIFIERS_RUNTIME_GENERATION_TO_4_7 = 434
	SERIALIZE_LANDSCAPE_GRASS_DATA = 435
	OPTIONALLY_CLEAR_GPU_EMITTERS_ON_INIT = 436
	SERIALIZE_LANDSCAPE_GRASS_DATA_MATERIAL_GUID = 437
	BLUEPRINT_GENERATED_CLASS_COMPONENT_TEMPLATES_PUBLIC = 438
	ACTOR_COMPONENT_CREATION_METHOD = 439
	K2NODE_EVENT_MEMBER_REFERENCE = 440
	STRUCT_GUID_IN_PROPERTY_TAG = 441
	REMOVE_UNUSED_UPOLYS_FROM_UMODEL = 442
	REBUILD_HIERARCHICAL_INSTANCE_TREES = 443
	PACKAGE_SUMMARY_HAS_COMPATIBLE_ENGINE_VERSION = 444
	TRACK_UCS_MODIFIED_PROPERTIES = 445
	LANDSCAPE_SPLINE_CROSS_LEVEL_MESHES = 446
	DEPRECATE_USER_WIDGET_DESIGN_SIZE = 447
	ADD_EDITOR_VIEWS = 448
	FOLIAGE_WITH_ASSET_OR_CLASS = 449
	BODYINSTANCE_BINARY_SERIALIZATION = 450
	SERIALIZE_BLUEPRINT_EVENTGRAPH_FASTCALLS_IN_UFUNCTION = 451
	INTERPCURVE_SUPPORTS_LOOPING = 452
	MATERIAL_INSTANCE_BASE_PROPERTY_OVERRIDES_DITHERED_LOD_TRANSITION = 453
	SERIALIZE_LANDSCAPE_ES2_TEXTURES = 454
	CONSTRAINT_INSTANCE_MOTOR_FLAGS = 455
	SERIALIZE_PINTYPE_CONST = 456
	LIBRARY_CATEGORIES_AS_FTEXT = 457
	SKIP_DUPLICATE_EXPORTS_ON_SAVE_PACKAGE = 458
	SERIALIZE_TEXT_IN_PACKAGES = 459
	ADD_BLEND_MODE_TO_WIDGET_COMPONENT = 460
	NEW_LIGHTMASS_PRIMITIVE_SETTING = 461
	REPLACE_SPRING_NOZ_PROPERTY = 462
	TIGHTLY_PACKED_ENUMS = 463
	ASSET_IMPORT_DATA_AS_JSON = 464
	TEXTURE_LEGACY_GAMMA = 465
	ADDED_NATIVE_SERIALIZATION_FOR_IMMUTABLE_STRUCTURES = 466
	DEPRECATE_UMG_STYLE_OVERRIDES = 467
	STATIC_SHADOWMAP_PENUMBRA_SIZE = 468
	NIAGARA_DATA_OBJECT_DEV_UI_FIX = 469
	FIXED_DEFAULT_ORIENTATION_OF_WIDGET_COMPONENT = 470
	REMOVED_MATERIAL_USED_WITH_UI_FLAG = 471
	CHARACTER_MOVEMENT_ADD_BRAKING_FRICTION = 472
	BSP_UNDO_FIX = 473
	DYNAMIC_PARAMETER_DEFAULT_VALUE = 474
	STATIC_MESH_EXTENDED_BOUNDS = 475
	ADDED_NON_LINEAR_TRANSITION_BLENDS = 476
	AO_MATERIAL_MASK = 477
	NAVIGATION_AGENT_SELECTOR = 478
	MESH_PARTICLE_COLLISIONS_CONSIDER_PARTICLE_SIZE = 479
	BUILD_MESH_ADJ_BUFFER_FLAG_EXPOSED = 480
	MAX_ANGULAR_VELOCITY_DEFAULT = 481
	APEX_CLOTH_TESSELLATION = 482
	DECAL_SIZE = 483
	KEEP_ONLY_PACKAGE_NAMES_IN_STRING_ASSET_REFERENCES_MAP = 484
	COOKED_ASSETS_IN_EDITOR_SUPPORT = 485
	DIALOGUE_WAVE_NAMESPACE_AND_CONTEXT_CHANGES = 486
	MAKE_ROT_RENAME_AND_REORDER = 487
	K2NODE_VAR_REFERENCEGUIDS = 488
	SOUND_CONCURRENCY_PACKAGE = 489
	USERWIDGET_DEFAULT_FOCUSABLE_FALSE = 490
	BLUEPRINT_CUSTOM_EVENT_CONST_INPUT = 491
	USE_LOW_PASS_FILTER_FREQ = 492
	NO_ANIM_BP_CLASS_IN_GAMEPLAY_CODE = 493
	SCS_STORES_ALLNODES_ARRAY = 494
	FBX_IMPORT_DATA_RANGE_ENCAPSULATION = 495
	CAMERA_COMPONENT_ATTACH_TO_ROOT = 496
	INSTANCED_STEREO_UNIFORM_UPDATE = 497
	STREAMABLE_TEXTURE_MIN_MAX_DISTANCE = 498
	INJECT_BLUEPRINT_STRUCT_PIN_CONVERSION_NODES = 499
	INNER_ARRAY_TAG_INFO = 500
	FIX_SLOT_NAME_DUPLICATION = 501
	STREAMABLE_TEXTURE_AABB = 502
	PROPERTY_GUID_IN_PROPERTY_TAG = 503
	NAME_HASHES_SERIALIZED = 504
	INSTANCED_STEREO_UNIFORM_REFACTOR = 505
	COMPRESSED_SHADER_RESOURCES = 506
	PRELOAD_DEPENDENCIES_IN_COOKED_EXPORTS = 507
	TemplateIndex_IN_COOKED_EXPORTS = 508
	PROPERTY_TAG_SET_MAP_SUPPORT = 509
	ADDED_SEARCHABLE_NAMES = 510

	LATEST_VERSION = 510

def hexdump(buf, text, start=0, width=16, indent=0):
	a = ''
	pr_headers(' ' * indent + text, end=':')
	for i, b in enumerate(buf):
		if i % width == 0:
			if i:
				pr_headers(' | %s |' % a)
			else:
				pr_headers()
			pr_headers('%s  %08x: ' % (' ' * indent, start + i), end='')
			a = ''
		elif i and i % 4 == 0:
			pr_headers(' ', end='')
		if b >= ord(' ') and b <= ord('~'):
			a += chr(b)
		else:
			a += '.'
		pr_headers('%02X' % b, end='')
	if a:
		rem = width - (i % width) - 1
		pr_headers(' ' * (rem*2), end='')
		pr_headers(' ' * (rem//4 + 1), end='')
		pr_headers('| %s%s |' % (a, ' ' * rem))

class parser(object):
	def u8(self):
		return struct.unpack('<B', self.f.read(1))[0]
	def s8(self):
		return struct.unpack('<b', self.f.read(1))[0]
	def u16(self):
		return struct.unpack('<H', self.f.read(2))[0]
	def s16(self):
		return struct.unpack('<h', self.f.read(2))[0]
	def u32(self):
		return struct.unpack('<I', self.f.read(4))[0]
	def s32(self):
		return struct.unpack('<i', self.f.read(4))[0]
	def u64(self):
		return struct.unpack('<Q', self.f.read(8))[0]
	def s64(self):
		return struct.unpack('<q', self.f.read(8))[0]
	def bool(self):
		b, = struct.unpack('<I', self.f.read(4))
		assert (b == 0 or b == 1)
		return not not b
	def float(self):
		return struct.unpack('<f', self.f.read(4))[0]
	def read(self, length=None):
		return self.f.read(length)
	def unknown(self, len, show=True, text='Unknown', start=None, indent=0):
		if not len:
			return
		if start is None:
			start = self.f.tell()
		buf = self.read(len)

		if not show:
			return buf

		hexdump(buf, '%s (%u bytes)' % (text, len), start=start, indent=indent)
		return buf

	def tell(self):
		return self.f.tell()
	def seek(self, *a, **kw):
		return self.f.seek(*a, **kw)
	def fileno(self):
		return self.f.fileno()
	def find(self, sub, start, end):
		pos = self.f.tell()
		buf = self.f.read(end)
		self.f.seek(pos)
		r = buf.find(sub, start, end)
		if r == -1:
			raise ItemError(r)
		return r

class file_parser(parser):
	def __init__(self, filename):
		self.f = open(filename, 'rb')

class buf_parser(parser):
	def __init__(self, buf):
		self.f = io.BytesIO(buf)

def TArrayU8(f):
	# Engine/Source/Runtime/Core/Public/Containers/Array.h operator<<
	ArrayNum = f.s32()
	return f.read(ArrayNum)

def TArrayU32(f):
	# Engine/Source/Runtime/Core/Public/Containers/Array.h operator<<
	ArrayNum = f.s32()
	return struct.unpack('%iI' % ArrayNum, f.read(ArrayNum * 4))

def TArrayS32(f):
	ArrayNum = f.s32()
	return struct.unpack('%ii' % ArrayNum, f.read(ArrayNum * 4))

def TArrayObject(f, constructor, *args, **kwargs):
	ArrayNum = f.s32()
	ret = []
	for i in range(ArrayNum):
		ret.append(constructor(f, *args, **kwargs))
	return ret

def FGuid(f, indent=0):
	return(' ' * indent + '%08x-%08x-%08x-%08x' % struct.unpack('4I', f.read(16)))

class FString(object):
	def __init__(self, f):
		# Engine/Source/Runtime/Core/Private/Containers/String.cpp operator<<
		SaveNum = f.s32()
		LoadUCS2Char = SaveNum < 0
		SaveNum = abs(SaveNum)
		# pr_debug('SaveNum: %i' % SaveNum)
		if LoadUCS2Char:
			self.raw = f.read(SaveNum * 2)
			self.encoding = 'utf16'
		else:
			self.raw = f.read(SaveNum)
			self.encoding = 'ascii'
		self.string = self.raw.decode(self.encoding).rstrip('\0')

	def __str__(self):
		return self.string

	def __bytes__(self):
		return self.raw

	def __eq__(self, other):
		return self.raw == other.raw

def FHash(f):
	return codecs.encode(f.read(20), 'hex').decode('ascii')

def shader_hash(bytecode):
	if args.hash == 'embedded':
		# The embedded hash is a 16 byte hash, but we only use 8:
		return int(codecs.encode(bytecode[4:12], 'hex'), 16)
	if args.hash == '3dmigoto':
		return fnv_3Dmigoto_shader(bytecode)
	raise NotImplemented()

def export_shader(bytecode):
	assert(bytecode[0:4] == b'DXBC')
	# TODO: Support other 3DMigoto hash types

	headers = end_headers()

	hash = shader_hash(bytecode)
	# FIXME: Determine shader type somehow
	base_filename = 'extracted/%016x-XX' % hash
	try:
		os.mkdir('extracted')
	except FileExistsError:
		pass

	export_dx11_shader(base_filename, bytecode, headers)

def parse_ue4_shader_code(Code):
	f = buf_parser(Code)

	# Engine/Source/Runtime/ShaderCore/Public/ShaderCore.h
	#   inline FArchive& operator<<(FArchive& Ar, FBaseShaderResourceTable& SRT)
	ResourceTableBits = f.u32()
	ShaderResourceViewMap = TArrayU32(f)
	SamplerMap = TArrayU32(f)
	UnorderedAccessViewMap = TArrayU32(f)
	ResourceTableLayoutHashes = TArrayU32(f)
	pr_headers('ResourceTableBits:', '%08x' % ResourceTableBits)
	pr_headers('ShaderResourceViewMap:',     ' '.join(map(lambda x: '%08x' % x, ShaderResourceViewMap)))
	pr_headers('SamplerMap:',                ' '.join(map(lambda x: '%08x' % x, SamplerMap)))
	pr_headers('UnorderedAccessViewMap:',    ' '.join(map(lambda x: '%08x' % x, UnorderedAccessViewMap)))
	pr_headers('ResourceTableLayoutHashes:', ' '.join(map(lambda x: '%08x' % x, ResourceTableLayoutHashes)))

	# This is in the UE4 source, but doesn't seem to be in the file?
	# Different engine versions perhaps? The tail in ABZU is different.
	# Engine/Source/Developer/Windows/ShaderFormatD3D/Private/D3D11ShaderCompiler.cpp
	# CompileD3D11Shader() - search for Output.Code
	#   Output.Code.Add(bGlobalUniformBufferUsed);
	#   Output.Code.Add(NumSamplers);
	#   Output.Code.Add(NumSRVs);
	#   Output.Code.Add(NumCBs);
	#   Output.Code.Add(NumUAVs);
	#  Note - if these are present, they should be *one byte* each

	# I'm not sure where the source is corresponding to this tail - I might
	# need to see what has changed since the last time I pulled the UE4 source
	# Looks like it contains the .usf filename and some other useful info...
	tail_len = Code[-1]
	hexdump(Code[-tail_len:-1], 'Unknown Tail (%u bytes)' % (tail_len - 1))

	return Code[f.tell() : -tail_len]

def parse_ue4_shader(f):
	start_headers()
	Type = FString(f)
	pr_headers('Type:', Type)
	EndOffset = f.u32()
	pr_debug('EndOffset: 0x%x' % EndOffset)

	# Way to have a flag embedded >in the file< indicating if this section
	# is present or not @Epic... Fail...
	bHandleShaderKeyChanges = False
	if bHandleShaderKeyChanges:
		# Engine/Source/Runtime/ShaderCore/Private/Shader.cpp
		#   FArchive& operator<<(FArchive& Ar,class FSelfContainedShaderId& Ref)
		#
		# Engine/Source/Runtime/Core/Public/Misc/SecureHash.h
		#   FSHAHash MaterialShaderMapHash - 16 bytes
		# FString VertexFactoryTypeName
		# FSHAHash VFSourceHash
		# FSerializationHistory VFSerializationHistory
		# FString ShaderTypeName
		# FSHAHash SourceHash
		# FSerializationHistory SerializationHistory
		# FShaderTarget Target;
		assert(False)

	# XXX: This file format is NOT WELL DEFINED and that is an EPIC FAIL!
	# The fields in this section may be SHADER SPECIFIC & GAME SPECIFIC!
	# There is no field that indicates the length of this section, so we
	# cannot reliably skip over it to get to the generic info we are after.
	# We take advantage of the fact that the shader type string is repeated
	# in the generic info after this section (which itself shows how poorly
	# designed the format is, but whatever - at least it is something we
	# can use. @Epic, if you fix that, please add a length field so we can
	# skip over the shader type specifc fields that we don't care about).
	# Look for any class that is derived from FShader (or other children
	# like FGlobalShader, etc) that has a ::Serialize() method. e.g.
	# Engine/Source/Runtime/Renderer/Private/ShaderBaseClasses.cpp
	# Engine/Source/Runtime/SlateRHIRenderer/Private/SlateMaterialShader.cpp
	# Engine/Source/Runtime/SlateRHIRenderer/Private/SlateShaders.cpp
	# And of course... these can be defined/overridden on a per game basis,
	# so the source code to the engine only helps us in some cases :(

	# Engine/Source/Runtime/ShaderCore/Private/Shader.cpp
	#   bool FShader::SerializeBase(FArchive& Ar, bool bShadersInline)

	# Ar << OutputHash;
	# Ar << MaterialShaderMapHash;
	# Ar << VFType;
	# Ar << VFSourceHash;

	# XXX: Could potentially work backwards from below to find the
	# preceeding fields we skipped over. It is worth noting that OutputHash
	# in this section is repeated after the code if the shader is inlined.

	off = f.find(bytes(Type), 0, EndOffset - f.tell())
	f.unknown(off, text='Skipping over variable length shader specific section')
	# Ar << Type;
	f.seek(f.tell() + len(bytes(Type)))

	SourceHash = FHash(f)
	pr_headers('SourceHash:', SourceHash)

	# Engine/Source/Runtime/ShaderCore/Public/ShaderCore.h
	#   friend FArchive& operator<<(FArchive& Ar,FShaderTarget& Target)
	TargetFrequency = f.u32()
	TargetPlatform = f.u32()
	pr_headers('TargetFrequency: %u, TargetPlatform: %u' % (TargetFrequency, TargetPlatform))

	NumUniformParameters = f.s32()
	pr_headers('NumUniformParameters: %i' % NumUniformParameters)
	for ParameterIndex in range(NumUniformParameters):
		StructName = FString(f)
		pr_headers('  StructName: %s' % StructName)
		# Grrr! The fields here can be parameter type specific:
		#   FUniformBufferStruct* Struct = FindUniformBufferStructByName(*StructName);
		#   FShaderUniformBufferParameter* Parameter = Struct ? Struct->ConstructTypedParameter() : new FShaderUniformBufferParameter();
		# With any luck they are all generic, but if not this could be a
		# deal breaker. If they are generic this should work:
		#   UnrealEngine/Engine/Source/Runtime/ShaderCore/Public/ShaderParameters.h
		#   FShaderUniformBufferParameter::Serialize()
		BaseIndex = f.u16() # NOTE: There is an accessor method that casts this to 32bit
		bIsBound = f.u32() # A bool... God damnit, read a book on defining file formats
		pr_headers('   BaseIndex: %u, bIsBound: %u' % (BaseIndex, bIsBound))

	# And again - way to have a flag embedded in the file to indicate that
	# this section is present @Epic Fail...
	bShadersInline = True
	if bShadersInline:
		# Engine/Source/Runtime/ShaderCore/Private/Shader.cpp
		#   FShaderResource::Serialize
		#     FArchive& operator<<(FArchive& Ar,FShaderType*& Ref)
		ShaderTypeName = FString(f)
		pr_headers('ShaderTypeName:', ShaderTypeName)
		TargetFrequency1 = f.u32()
		TargetPlatform1 = f.u32()
		assert(TargetFrequency == TargetFrequency1)
		assert(TargetPlatform == TargetPlatform1)
		#     Ar << Code;
		Code = TArrayU8(f)
		dxbc = parse_ue4_shader_code(Code)
		OutputHash = FHash(f)
		pr_headers('OutputHash:', OutputHash) # Repeated from above in the section we skipped over
		NumInstructions = f.u32()
		pr_headers('NumInstructions:', NumInstructions)
		NumTextureSamplers = f.u32()
		pr_headers('NumTextureSamplers:', NumTextureSamplers)

	f.unknown(EndOffset - f.tell())

	export_shader(dxbc)

def parse_ue4_global_shader_cache(f):
	'''
	e.g. Engine/GlobalShaderCache-PCD3D_SM5.bin
	'''
	# Engine/Source/Runtime/Engine/Private/GlobalShader.cpp SerializeGlobalShaders
	assert(f.u32() == 0x47534D42) # Endian swapped "GSMB"

	# Engine/Source/Runtime/ShaderCore/Public/Shader.h TShaderMap::SerializeInline
	NumShaders = f.u32()
	print('NumShaders: %i' % NumShaders)

	for i in range(NumShaders):
		pr_debug()
		parse_ue4_shader(f)

	print()

	cur = f.tell()
	end = os.fstat(f.fileno()).st_size
	pr_debug('Current position: 0x%x / 0x%x' % (cur, end))
	f.unknown(end - cur)

def parse_batman_cooked_shader_cache(f):
	'''
	Parses a cooked shader cache from UE3.5, e.g.
	*/CookedPCConsole/GlobalShaderCache-PC-D3D-SM5.bin

	Material shaders and uncooked shaders are elsewhere and not parsed yet

	This might be specific to Arkham Knight for now
	'''
	# Engine/Source/Runtime/Engine/Private/GlobalShader.cpp SerializeGlobalShaders
	assert(f.u32() == 0x47534D42) # Endian swapped "GSMB"

	ret = {}

	# NFI - can't see this in the source code anywhere:
	f.unknown(17)

	# Engine/Source/Runtime/ShaderCore/Public/Shader.h TShaderMap::SerializeInline
	NumShaders = f.u32()
	print('NumShaders: %i' % NumShaders)

	for i in range(NumShaders):
		print()

		# Format used in Batman does not seem to match UE4 source code?
		# Update: Batman is a heavily modified version of UE3.5, not UE4

		Name = FString(f)
		print('Name:', Name)

		u1 = f.unknown(8)
		u2 = f.unknown(20)

		EndOffset = f.u32()
		pr_debug('EndOffset: 0x%x' % EndOffset)

		# Possibly an index of resources?
		table_len = f.u32()
		pr_debug('Unknown Table Length: %i\n ' % table_len, end='')
		for j in range(table_len):
			u = f.u32()
			pr_debug("%i, " % u, end='')
		pr_debug()

		f.unknown(2)

		bytecode_len = f.u32()
		pr_debug('Bytecode Len:', bytecode_len)

		bytecode = f.read(bytecode_len)
		# pr_debug('Bytecode:', bytecode)
		assert(bytecode[0:4] == b'DXBC')

		hash = shader_hash(bytecode)
		print('%s hash: %016x' % (args.hash, hash))

		u1a = f.unknown(8, show=False)
		assert(u1 == u1a)

		Name1 = FString(f)
		# pr_debug('Name1:', Name)
		if Name != Name1:
			print('Names differ!')

		u2a = f.unknown(20, show=False)
		assert(u2 == u2a)

		tail = EndOffset - f.tell()
		f.unknown(tail)

		ret[hash] = Name

	print()

	cur = f.tell()
	end = os.fstat(f.fileno()).st_size
	pr_debug('Current position: 0x%x / 0x%x' % (cur, end))
	f.unknown(end - cur)

	return ret

def parse_shader_cache(f):
	if args.batman:
		shader_names = parse_batman_cooked_shader_cache(f)
		for shader in args.files[1:]:
			fnv = int(os.path.basename(shader)[0:16], 16)
			if fnv in shader_names:
				print('%s: %s' % (shader, shader_names[fnv]))
	else:
		parse_ue4_global_shader_cache(f)

def parse_custom_version_section(f, LegacyFileVersion):
	# static ECustomVersionSerializationFormat::Type GetCustomVersionFormatForArchive(int32 LegacyFileVersion)
	# Engine/Source/Runtime/Core/Private/Serialization/CustomVersion.cpp
	if LegacyFileVersion < -5: # Optimized
		# TSet, which contains a TSparseArray, which stores number of elements
		# followed by a list, the serizlisation of each should be in
		# Engine/Source/Runtime/Core/Private/Serialization/CustomVersion.cpp:
		NewNumElements = f.s32()
		# In ABZU this is 0, assert that for now and deal with it later:
		# NOTE: FMaterialUniformExpressionFoldedMath() uses this
		assert(NewNumElements == 0)
	elif LegacyFileVersion < -2: # Guids
		raise NotImplemented()
	elif LegacyFileVersion == -2: # Enums
		raise NotImplemented()

class Parser(object):
	def __init__(self, indent=0):
		self.indent = indent

	def parse(self, name, val, fmt='{}'):
		pr_debug(('{}{}: %s' % fmt).format(' ' * self.indent, name, val))
		setattr(self, name, val)
	p = parse

	def n(self, name):
		pr_debug('{}{}:'.format(' ' * self.indent, name))

class Generation(Parser):
	def __init__(self, f, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('ExportCount', f.s32())
		p('NameCount', f.s32())

class FEngineVersion(Parser):
	def __init__(self, f, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('Major', f.s16())
		p('Minor', f.s16())
		p('Patch', f.s16())
		p('Changelists', f.u32())
		p('Branch', FString(f))

class FCompressedChunk(Parser):
	def __init__(self, f, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('UncompressedOffset', f.s32())
		p('UncompressedSize', f.s32())
		p('CompressedOffset', f.s32())
		p('CompressedSize', f.s32())

class PackageFileSummary(Parser):
	# Engine/Source/Runtime/CoreUObject/Private/UObject/PackageFileSummary.cpp
	def __init__(self, f, indent=0):
		# FArchive& operator<<( FArchive& Ar, FPackageFileSummary& Sum )
		Parser.__init__(self, indent)
		p = self.parse
		assert(f.u32() == 0x9E2A83C1) # PACKAGE_FILE_TAG / PACKAGE_FILE_TAG_SWAPPED

		# See comment in the source about what this signifies:
		p('LegacyFileVersion', f.s32())
		assert(self.LegacyFileVersion == -6) # ABZU, only one tested
		if self.LegacyFileVersion != -4:
			p('LegacyUE3Version', f.s32())

		p('FileVersionUE4', f.s32())
		p('FileVersionLicenseeUE4', f.s32())

		parse_custom_version_section(f, self.LegacyFileVersion)

		p('TotalHeaderSize', f.s32())
		p('FolderName', FString(f))
		p('PackageFlags', f.u32(), '{:08x}')
		p('NameCount', f.s32())
		p('NameOffset', f.s32(), '0x{:x}')

		if self.FileVersionUE4 >= VER_UE4.SERIALIZE_TEXT_IN_PACKAGES:
			p('GatherableTextDataCount', f.s32())
			p('GatherableTextDataOffset', f.s32(), '0x{:x}')

		p('ExportCount', f.s32())
		p('ExportOffset', f.s32(), '0x{:x}')
		p('ImportCount', f.s32())
		p('ImportOffset', f.s32(), '0x{:x}')
		p('DependsOffset', f.s32(), '0x{:x}')

		assert(self.FileVersionUE4 >= VER_UE4.OLDEST_LOADABLE_PACKAGE)
		assert(self.FileVersionUE4 <= VER_UE4.LATEST_VERSION) # XXX Incremented as the format changes

		if self.FileVersionUE4 >= VER_UE4.ADD_STRING_ASSET_REFERENCES_MAP:
			p('StringAssetReferencesCount', f.s32())
			p('StringAssetReferencesOffset', f.s32(), '0x{:x}')

		if self.FileVersionUE4 >= VER_UE4.ADDED_SEARCHABLE_NAMES:
			p('SearchableNamesOffset', f.s32(), '0x{:x}')

		p('ThumbnailTableOffset', f.s32(), '0x{:x}')
		p('Guid', FGuid(f))

		p('GenerationCount', f.s32())
		self.generations = []
		for i in range(self.GenerationCount):
			self.generations.append(Generation(f, indent=2))

		if self.FileVersionUE4 >= VER_UE4.ENGINE_VERSION_OBJECT:
			pr_debug('SavedByEngineVersion:')
			self.SavedByEngineVersion = FEngineVersion(f, indent=2)
		else:
			p('EngineChangelist', f.s32())

		if self.FileVersionUE4 >= VER_UE4.PACKAGE_SUMMARY_HAS_COMPATIBLE_ENGINE_VERSION:
			pr_debug('CompatibleWithEngineVersion:')
			self.CompatibleWithEngineVersion = FEngineVersion(f, indent=2)

		p('CompressionFlags', f.u32(), '{:08x}')
		pr_debug('CompressedChunks:')
		self.CompressedChunks = TArrayObject(f, FCompressedChunk, indent=2)
		p('PackageSource', f.u32(), '{:08x}')
		pr_debug('AdditionalPackagesToCook:')
		self.AdditionalPackagesToCook = TArrayObject(f, FString, indent=2)

		if self.LegacyFileVersion > -7:
			p('NumTextureAllocations', f.s32())

		p('AssetRegistryDataOffset', f.s32(), '0x{:08x}')
		p('BulkDataStartOffset', f.s64(), '0x{:016x}')

		if self.FileVersionUE4 >= VER_UE4.WORLD_LEVEL_INFO:
			p('WorldTileInfoDataOffset', f.s32(), '0x{:08x}')

		if self.FileVersionUE4 >= VER_UE4.CHANGED_CHUNKID_TO_BE_AN_ARRAY_OF_CHUNKIDS:
			p('ChunkIDs', TArrayS32(f))
		elif self.FileVersionUE4 >= VER_UE4.ADDED_CHUNKID_TO_ASSETDATA_AND_UPACKAGE:
			raise NotImplemented()

		if self.FileVersionUE4 >= VER_UE4.PRELOAD_DEPENDENCIES_IN_COOKED_EXPORTS:
			p('PreloadDependencyCount', f.s32())
			p('PreloadDependencyOffset', f.s32(), '0x{:x}')

class FObjectExport(Parser):
	# Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
	def __init__(self, f, s, FName, indent=0):
		# FArchive& operator<<( FArchive& Ar, FObjectExport& E )
		Parser.__init__(self, indent)
		p = self.parse
		p('ClassIndex', f.s32())
		p('SuperIndex', f.s32())
		if s.FileVersionUE4 >= VER_UE4.TemplateIndex_IN_COOKED_EXPORTS:
			p('TemplateIndex', f.s32())
		p('OuterIndex', f.s32())
		p('ObjectName', FName(f))
		p('ObjectFlags', f.u32(), '{:08x}')
		p('SerialSize', f.s32())
		p('SerialOffset', f.u32(), '0x{:x}')
		p('bForcedExport', f.bool())
		p('bNotForClient', f.bool())
		p('bNotForServer', f.bool())
		p('PackageGuid', FGuid(f))
		p('PackageFlags', f.u32(), '{:08x}')
		if s.FileVersionUE4 >= VER_UE4.LOAD_FOR_EDITOR_GAME:
			p('bNotForEditorGame', f.bool())
		if s.FileVersionUE4 >= VER_UE4.COOKED_ASSETS_IN_EDITOR_SUPPORT:
			p('bIsAsset', f.bool())
		if s.FileVersionUE4 >= VER_UE4.PRELOAD_DEPENDENCIES_IN_COOKED_EXPORTS:
			p('FirstExportDependency', f.s32())
			p('SerializationBeforeSerializationDependencies', f.s32())
			p('CreateBeforeSerializationDependencies', f.s32())
			p('SerializationBeforeCreateDependencies', f.s32())
			p('CreateBeforeCreateDependencies', f.s32())

class FObjectImport(Parser):
	# Engine/Source/Runtime/CoreUObject/Private/UObject/ObjectResource.cpp
	def __init__(self, f, s, FName, indent=0):
		# FArchive& operator<<( FArchive& Ar, FObjectExport& E )
		Parser.__init__(self, indent)
		p = self.parse
		p('ClassPackage', FName(f))
		p('ClassName', FName(f))
		p('OuterIndex', f.s32())
		p('ObjectName', FName(f))

class FStaticSwitchParameter(Parser):
	def __init__(self, f, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('ParameterName', FName(f))
		p('Value', f.bool())
		p('bOverride', f.bool())
		p('ExpressionGUID', FGuid(f))

class FStaticComponentMaskParameter(Parser):
	def __init__(self, f, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('ParameterName', FName(f))
		p('R', f.bool())
		p('G', f.bool())
		p('B', f.bool())
		p('A', f.bool())
		p('bOverride', f.bool())
		p('ExpressionGUID', FGuid(f))

class FStaticTerrainLayerWeightParameter(Parser):
	def __init__(self, f, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('ParameterName', FName(f))
		p('WeightmapIndex', f.s32())
		p('bOverride', f.bool())
		p('ExpressionGUID', FGuid(f))

class FStaticParameterSet(Parser):
	# Engine/Source/Runtime/Engine/Public/StaticParameterSet.h
	def __init__(self, f, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		pr_debug('{}StaticSwitchedParameters:'.format(' '*indent))
		self.StaticSwitchedParameters = TArrayObject(f, FStaticSwitchParameter, FName, indent=indent+2)
		pr_debug('{}StaticComponentMaskParameters:'.format(' '*indent))
		self.StaticComponentMaskParameters = TArrayObject(f, FStaticComponentMaskParameter, FName, indent=indent+2)
		pr_debug('{}TerrainLayerWeightParameters:'.format(' '*indent))
		self.TerrainLayerWeightParameters = TArrayObject(f, FStaticTerrainLayerWeightParameter, FName, indent=indent+2)

class FShaderTypeDependency(Parser):
	def __init__(self, f, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('ShaderTypeName', FName(f))
		p('SourceHash', FHash(f))

class FShaderPipelineTypeDependency(Parser):
	def __init__(self, f, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('ShaderPipelineType', FName(f))
		p('StagesSourceHash', FHash(f))

class FVertexFactoryTypeDependency(Parser):
	def __init__(self, f, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('VertexFactoryType', FName(f))
		p('VFSourceHash', FHash(f))

class FMaterialShaderMapId(Parser):
	# Engine/Source/Runtime/Engine/Private/Materials/MaterialShader.cpp
	def __init__(self, f, s, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('UsageInt', f.u32())
		p('BaseMaterialId', FGuid(f))

		if s.FileVersionUE4 >= VER_UE4.PURGED_FMATERIAL_COMPILE_OUTPUTS:
			p('QualityLevel', f.s32())
			p('FeatureLevel', f.s32())
		else:
			p('LegacyQualityLevel', f.u8())

		pr_debug('{}ParameterSet:'.format(' '*indent))
		self.ParameterSet = FStaticParameterSet(f, FName, indent=indent+2)

		pr_debug('{}ReferencedFunctions:'.format(' '*indent))
		self.ReferencedFunctions = TArrayObject(f, FGuid, indent=indent+2)

		if s.FileVersionUE4 >= VER_UE4.COLLECTIONS_IN_SHADERMAPID:
			pr_debug('{}ReferencedParameterCollections:'.format(' '*indent))
			self.ReferencedParameterCollections = TArrayObject(f, FGuid, indent=indent+2)

		pr_debug('{}ShaderTypeDependencies:'.format(' '*indent))
		self.ShaderTypeDependencies = TArrayObject(f, FShaderTypeDependency, FName, indent=indent+2)

		if s.FileVersionUE4 >= VER_UE4.PURGED_FMATERIAL_COMPILE_OUTPUTS:
			pr_debug('{}ShaderPipelineTypeDependencies:'.format(' '*indent))
			self.ShaderPipelineTypeDependencies = TArrayObject(f, FShaderPipelineTypeDependency, FName, indent=indent+2)

		pr_debug('{}VertexFactoryTypeDependencies:'.format(' '*indent))
		self.VertexFactoryTypeDependencies = TArrayObject(f, FVertexFactoryTypeDependency, FName, indent=indent+2)

		if s.FileVersionUE4 >= VER_UE4.PURGED_FMATERIAL_COMPILE_OUTPUTS:
			p('TextureReferencesHash', FHash(f))
		else:
			p('LegacyHash', FHash(f))

		if s.FileVersionUE4 >= VER_UE4.MATERIAL_INSTANCE_BASE_PROPERTY_OVERRIDES:
			p('BasePropertyOverridesHash', FHash(f))

class FLinearColor(Parser):
	def __init__(self, f, s, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('R', f.float())
		p('G', f.float())
		p('B', f.float())
		p('A', f.float())

class FMaterialUniformExpression(Parser):
	class FMaterialUniformExpressionVectorParameter(Parser):
		def __init__(self, f, s, FName, indent=0):
			Parser.__init__(self, indent)
			self.p('ParameterName', FName(f))
			self.n('DefaultValue')
			self.DefaultValue = FLinearColor(f, s, FName, indent+2)
	class FMaterialUniformExpressionComponentSwizzle(Parser):
		def __init__(self, f, s, FName, indent=0):
			Parser.__init__(self, indent)
			self.n('X')
			FMaterialUniformExpression(f, s, FName, indent+2)
			self.p('IndexR', f.s8())
			self.p('IndexG', f.s8())
			self.p('IndexB', f.s8())
			self.p('IndexA', f.s8())
			self.p('NumElements', f.s8())
	class FMaterialUniformExpressionFoldedMath(Parser):
		def __init__(self, f, s, FName, indent=0):
			Parser.__init__(self, indent)
			self.n('A')
			FMaterialUniformExpression(f, s, FName, indent+2)
			self.n('B')
			FMaterialUniformExpression(f, s, FName, indent+2)
			self.p('Op', f.u8())
			# FIXME	if (Ar.CustomVer(FRenderingObjectVersion::GUID) >= FRenderingObjectVersion::TypeHandlingForMaterialSqrtNodes) {
			#   self.p('ValueType', f.u32())
			# }
	class FMaterialUniformExpressionConstant(Parser):
		def __init__(self, f, s, FName, indent=0):
			Parser.__init__(self, indent)
			self.n('Value')
			self.DefaultValue = FLinearColor(f, s, FName, indent+2)
			self.p('ValueType', f.u8())
	class FMaterialUniformExpressionTexture(Parser):
		def __init__(self, f, s, FName, indent=0):
			Parser.__init__(self, indent)
			self.p('TextureIndex', f.s32())
			self.p('SamplerSourceInt', f.s32())

	# TODO: Implement remaining FMaterialUniformExpression*::Serialize routines (28 total)
	# Find FMaterialUniformExpression::operator<< and go to definition of Ref->Serialize() for list

	def __init__(self, f, s, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		p('TypeName', FName(f))
		getattr(self, str(self.TypeName))(f, s, FName, indent+2) # KeyError means we need to implement whatever was named in TypeName

# operator<< is the same, but Serialize() is different - see
# FMaterialUniformExpression.FMaterialUniformExpressionTexture
FMaterialUniformExpressionTexture = FMaterialUniformExpression

class FUniformExpressionSet(Parser):
	def __init__(self, f, s, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		n = self.n

		n('UniformVectorExpressions')
		self.UniformVectorExpressions = TArrayObject(f, FMaterialUniformExpression, s, FName, indent=indent+2)
		n('UniformScalarExpressions')
		self.UniformScalarExpressions = TArrayObject(f, FMaterialUniformExpression, s, FName, indent=indent+2)
		n('Uniform2DTextureExpressions')
		self.Uniform2DTextureExpressions = TArrayObject(f, FMaterialUniformExpressionTexture, s, FName, indent=indent+2)
		n('UniformCubeTextureExpressions')
		self.UniformCubeTextureExpressions = TArrayObject(f, FMaterialUniformExpressionTexture, s, FName, indent=indent+2)

		n('ParameterCollections')
		self.ParameterCollections = TArrayObject(f, FGuid, indent=indent+2)

		# Added in 961188323fe864b8bdc3c240a9903441ede8d9b9,
		# had been removed (from a different point above ParameterCollection)
		# earlier. First version actually had a version check, but since it was
		# re-added in a different spot, this might be broken anyway!
		if s.FileVersionUE4 >= VER_UE4.PERFRAME_MATERIAL_UNIFORM_EXPRESSIONS:
			n('PerFrameUniformScalarExpressions')
			self.PerFrameUniformScalarExpressions = TArrayObject(f, FMaterialUniformExpression, s, FName, indent=indent+2)
			n('PerFrameUniformVectorExpressions')
			self.PerFrameUniformVectorExpressions = TArrayObject(f, FMaterialUniformExpression, s, FName, indent=indent+2)

		# XXX Added in 6d43349dfdf79856d0899bcdc56007866339abdb
		if s.FileVersionUE4 >= VER_UE4.ADD_MODIFIERS_RUNTIME_GENERATION: # 429
			n('PerFramePrevUniformScalarExpressions')
			self.PerFramePrevUniformScalarExpressions = TArrayObject(f, FMaterialUniformExpression, s, FName, indent=indent+2)
			n('PerFramePrevUniformVectorExpressions')
			self.PerFramePrevUniformVectorExpressions = TArrayObject(f, FMaterialUniformExpression, s, FName, indent=indent+2)


class FMaterialCompilationOutput(Parser):
	# Engine/Source/Runtime/Engine/Private/Materials/MaterialShared.cpp
	def __init__(self, f, s, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse
		FUniformExpressionSet(f, s, FName, indent)

		# The damn UE4 devs forgot to bump the file version when adding most of
		# these fields, and one douche even went so far as to remove one of the
		# checks they did have. Fucking Epic Fail right there! The version
		# numbers I've added are *prior* to the commits that added them, but I
		# haven't compared them to point releases, so some versions may fail.

		# Version check removed from source :facepalm:
		if s.FileVersionUE4 >= VER_UE4.PURGED_FMATERIAL_COMPILE_OUTPUTS: # 260
			p('bRequiresSceneColorCopy', f.bool())

		# XXX Added in 3f12c4b4bb38e346296fa3c33df579028f1568ab
		if s.FileVersionUE4 >= VER_UE4.SKELETON_ASSET_PROPERTY_TYPE_CHANGE: # 358
			p('bNeedsSceneTextures', f.bool())
			p('bUsesEyeAdaptation', f.bool())

		p('bModifiesMeshPosition', f.bool())

		# XXX Added in 0b102492a97b9455ab6d1ab9b7476507b3ec8c61
		if s.FileVersionUE4 >= VER_UE4.INSTANCED_STEREO_UNIFORM_REFACTOR: # 505
			p('bUsesWorldPositionOffset', f.bool())

		# XXX Added in b58498e8ae00ffe0396b13517a87f1444855ad03
		if s.FileVersionUE4 >= VER_UE4.LOAD_FOR_EDITOR_GAME: # 365
			p('bNeedsGBuffer', f.bool())

		# XXX Added in a973772ec9d9446a7cc8a178dd9d06daf3e26d89
		if s.FileVersionUE4 >= VER_UE4.SERIALIZE_TEXT_IN_PACKAGES: # 459
			p('bUsesGlobalDistanceField', f.bool())

		# XXX Added in f180dff1073b1ec6d9f0439e0d1a3c11f2540495
		if s.FileVersionUE4 >= VER_UE4.NAME_HASHES_SERIALIZED: # 504
			p('bUsesPixelDepthOffset', f.bool())

		# XXX Added in 093fd5df10f84848364746baf82ff6372bb4d76f
		if s.FileVersionUE4 >= VER_UE4.PRELOAD_DEPENDENCIES_IN_COOKED_EXPORTS: # 507
			p('bUsesSceneDepthLookup', f.bool())

		# Not sure if I've fucked up or what, but I need this for ABZU
		# (FileVersionUE4 = 498):
		f.unknown(4, indent=indent)

class FMaterialShaderMap(Parser):
	# Engine/Source/Runtime/Engine/Private/Materials/MaterialShader.cpp
	def __init__(self, f, s, FName, indent=0):
		Parser.__init__(self, indent)
		p = self.parse

		pr_debug('{}ShaderMapId:'.format(' '*indent))
		self.ShaderMapId = FMaterialShaderMapId(f, s, FName, indent+2)

		p('TempPlatform', f.s32()) # Comment says uint8, but it's an int32 @_@
		p('FriendlyName', FString(f))

		FMaterialCompilationOutput(f, s, FName, indent)

		# If this doesn't print, check the version checks in FMaterialCompilationOutput
		p('DebugDescription', FString(f))

def parse_name_map(f, s):
	# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# FPackageReader::SerializeNameMap()
	f.seek(s.NameOffset)
	names = []
	for i in range(s.NameCount):
		name = FString(f) # Actually an FNameEntrySerialized
		# pr_debug('  Name[%i]: %s' % (i, name))
		names.append(name)

	def FNamePackageReader(f, names):
		# There seem to be several implementations of FName, this one is from
		# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
		NameIndex = f.u32()
		Number = f.u32()
		if Number:
			return '%s[%i]' % (names[NameIndex], Number)
		return names[NameIndex]

	return lambda f: FNamePackageReader(f, names)

def parse_imports(f, s, FName):
	# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# FPackageReader::SerializeImportMap()
	f.seek(s.ImportOffset)
	imports = []
	for i in range(s.ImportCount):
		pr_debug('Import %i:' % i)
		imports.append(FObjectImport(f, s, FName, indent=2))
	return imports

def parse_exports(f, s, FName):
	# Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# FPackageReader::SerializeExportMap()
	f.seek(s.ExportOffset)
	exports = []
	for i in range(s.ExportCount):
		pr_debug('Export %i:' % i)
		exports.append(FObjectExport(f, s, FName, indent=2))

		offset = f.tell()
		f.seek(exports[-1].SerialOffset)
		if False and exports[-1].bIsAsset: # XXX Disabled
			# FIXME: Parse this properly, or at least determine size somehow -
			# I think it depends on the object class determined by the name?
			pr_debug('  Decoding contained asset:')
			f.unknown(0x380, start=0, indent=4) # XXX FIXME XXX FIXME XXX FIXME XXX FIXME XXX FIXME XXX FIXME XXX
			FMaterialShaderMap(f, s, FName, indent=4)
			f.unknown(exports[-1].SerialSize - f.tell() + offset, start=0)
		else:
			f.unknown(exports[-1].SerialSize, start=0)
		f.seek(offset)
	return exports

def parse_uasset(f):
	# ? Engine/Source/Runtime/AssetRegistry/Private/PackageReader.cpp
	# ? Engine/Source/Runtime/Core/Private/Serialization/Archive.cpp
	# ? Engine/Source/Runtime/CoreUObject/Private/UObject/SavePackage.cpp

	summary = PackageFileSummary(f)
	assert(not (summary.PackageFlags & 0x02000000)) # PKG_StoreCompressed
	FName = parse_name_map(f, summary)
	imports = parse_imports(f, summary, FName)
	exports = parse_exports(f, summary, FName)

def parse_args():
	global verbosity, args

	parser = argparse.ArgumentParser()
	parser.add_argument('files', nargs='*')
	parser.add_argument('--verbose', '-v', action='count', default=0)
	parser.add_argument('--batman', action='store_true')
	parser.add_argument('--hash', choices=['embedded', '3dmigoto']) # TODO: bytecode
	parser.add_argument('--acknowledge-this-script-is-abandoned-and-unsupported', action='store_true')
	args = parser.parse_args()

	if not args.acknowledge_this_script_is_abandoned_and_unsupported:
		print(textwrap.dedent('''
			This script has been abandoned due to considerable complications in the Unreal
			file formats. It can extract shader names from the Arkham Knight cooked shader
			cache, but probably won't do anything useful in any other game. Consider using
			the generic_shader_extractor.py script instead.

			To run the script anyway knowing that it is not supported, run again with
			--acknowledge-this-script-is-abandoned-and-unsupported
		'''))
		sys.exit(1)

	if not args.files:
		parser.error('no files specified')

	if args.hash is None:
		parser.error('--hash is required')

	verbosity = args.verbose

def main():
	parse_args()

	for filename in args.files:
		f = file_parser(filename)
		ext = os.path.splitext(filename)[1].lower()
		if ext == '.bin':
			parse_shader_cache(f)
		elif ext == '.uasset':
			parse_uasset(f)
		else:
			raise Exception('Unsupported file: %s' % filename)



if __name__ == '__main__':
	main()

# vi:noet:ts=4:sw=4
