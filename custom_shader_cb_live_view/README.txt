To use this debug shader, copy the files from ShaderFixes to your fix and add
this line to the [Include] section:

    [Include]
    include = ShaderFixes\debug_cb.ini

Then in the shader you want to examine live add a line like this to copy (or
reference) the constant buffer of interest to ResourceDebugCB:

    [ShaderOverrideCBDebugTest]
    hash = 3be9e2a31cdc60c2
    Resource\debug_cb\CB = ps-cb1

Or alternatively, to examine another type of buffer (including stereo buffers),
use ResourceDebugBuf instead (if both are set, ResourceDebugBuf takes
precedence):

    [ShaderOverrideCBDebugTest]
    hash = 3be9e2a31cdc60c2
    Resource\debug_cb\Buf = cs-u0
