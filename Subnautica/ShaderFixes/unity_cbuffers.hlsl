#define fixed4 float4

struct UnityPerCamera {
    // Time (t = time since current level load) values from Unity
    float4 _Time; // (t/20, t, t*2, t*3)
    float4 _SinTime; // sin(t/8), sin(t/4), sin(t/2), sin(t)
    float4 _CosTime; // cos(t/8), cos(t/4), cos(t/2), cos(t)
    float4 unity_DeltaTime; // dt, 1/dt, smoothdt, 1/smoothdt

#if !defined(UNITY_SINGLE_PASS_STEREO) && !defined(STEREO_INSTANCING_ON)
    float3 _WorldSpaceCameraPos;
    float UAV_PADDING_WorldSpaceCameraPos;
#endif

    // x = 1 or -1 (-1 if projection is flipped)
    // y = near plane
    // z = far plane
    // w = 1/far plane
    float4 _ProjectionParams;

    // x = width
    // y = height
    // z = 1 + 1.0/width
    // w = 1 + 1.0/height
    float4 _ScreenParams;

    // Values used to linearize the Z buffer (http://www.humus.name/temp/Linearize%20depth.txt)
    // x = 1-far/near
    // y = far/near
    // z = x/far
    // w = y/far
    float4 _ZBufferParams;

    // x = orthographic camera's width
    // y = orthographic camera's height
    // z = unused
    // w = 1.0 if camera is ortho, 0.0 if perspective
    float4 unity_OrthoParams;
};

struct UnityPerDraw {
#ifdef UNITY_USE_PREMULTIPLIED_MATRICES
    row_major float4x4 glstate_matrix_mvp;
    row_major float4x4 glstate_matrix_modelview0;
    row_major float4x4 glstate_matrix_invtrans_modelview0;
#endif

    row_major float4x4 unity_ObjectToWorld;
    row_major float4x4 unity_WorldToObject;
    float4 unity_LODFade; // x is the fade value ranging within [0,1]. y is x quantized into 16 levels
    float4 unity_WorldTransformParams; // w is usually 1.0, or -1.0 for odd-negative scale transforms
};

struct UnityPerFrame {
    /*  0 */ fixed4 glstate_lightmodel_ambient;
    /*  1 */ fixed4 unity_AmbientSky;
    /*  2 */ fixed4 unity_AmbientEquator;
    /*  3 */ fixed4 unity_AmbientGround;
    /*  4 */ fixed4 unity_IndirectSpecColor;

#if !defined(UNITY_SINGLE_PASS_STEREO) && !defined(STEREO_INSTANCING_ON)
    /*  5[4] */ row_major float4x4 glstate_matrix_projection;
    /*  9[4] */ row_major float4x4 unity_MatrixV;
    /* 13[4] */ row_major float4x4 unity_MatrixInvV; // Beware: May just be the identity matrix
    /* 17[4] */ row_major float4x4 unity_MatrixVP; // Beware: May be [2 0 0 0] [0 -2 0 0] [0 0 ~0.01 0] [-1 1 ~1 1] for post effects / HUD
    /* 21    */ int unity_StereoEyeIndex;
    float3 UAV_PADDING_unity_StereoEyeIndex;
#endif
};
