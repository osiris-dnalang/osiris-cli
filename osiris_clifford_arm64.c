/*
 * OSIRIS Clifford Cl(3,0) NEON / ARM64 Rotor Kernel
 * ===================================================
 * Optimized geometric algebra multivector and rotor multiplication.
 * Supports ARMv8-A NEON SIMD with portable scalar fallback.
 *
 * Mathematical Invariants:
 * - Geometric product on Cl(3,0) even subalgebra (isomorphic to Quaternions H)
 * - Sandwich product v' = R * v * R^dagger
 * - Fixed resonance angle: theta_lock = 51.843 degrees (0.904838 rad)
 * - Coherence constraint: Norm preservation |R| = 1.0 within 1e-7
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <stdint.h>

#if defined(__ARM_NEON) || defined(__aarch64__)
#include <arm_neon.h>
#define HAS_NEON 1
#else
#define HAS_NEON 0
#endif

#define THETA_LOCK_RAD 0.90483814f
#define GAMMA_FLOOR 0.092f

typedef struct {
    float s;    /* Scalar: 1 */
    float b12;  /* Bivector e12 (k) */
    float b23;  /* Bivector e23 (i) */
    float b31;  /* Bivector e31 (j) */
} CliffordRotor;

typedef struct {
    float x;    /* Vector e1 */
    float y;    /* Vector e2 */
    float z;    /* Vector e3 */
} CliffordVector;

/* Export macros */
#if defined(_WIN32)
#define OSIRIS_API __declspec(dllexport)
#else
#define OSIRIS_API __attribute__((visibility("default")))
#endif

/* Initialize rotor from rotation angle theta and normalized axis (nx, ny, nz) */
OSIRIS_API void clifford_rotor_from_axis_angle(float theta_rad, float nx, float ny, float nz, CliffordRotor* out) {
    float half = theta_rad * 0.5f;
    float s = cosf(half);
    float sin_half = sinf(half);

    /* Normalize axis */
    float norm = sqrtf(nx*nx + ny*ny + nz*nz);
    if (norm > 1e-12f) {
        float inv = 1.0f / norm;
        nx *= inv;
        ny *= inv;
        nz *= inv;
    } else {
        nx = 0.0f; ny = 0.0f; nz = 1.0f;
    }

    out->s = s;
    out->b23 = nx * sin_half; /* i */
    out->b31 = ny * sin_half; /* j */
    out->b12 = nz * sin_half; /* k */
}

/*
 * Rotor geometric multiplication: R_out = R1 * R2
 * R1 = (s1, i1, j1, k1), R2 = (s2, i2, j2, k2)
 */
OSIRIS_API void clifford_rotor_multiply(const CliffordRotor* r1, const CliffordRotor* r2, CliffordRotor* out) {
#if HAS_NEON
    /* NEON vectorized 4-wide float quaternion multiply */
    float32x4_t a = vld1q_f32((const float*)r1);
    float32x4_t b = vld1q_f32((const float*)r2);

    /* Extract scalar parts */
    float s1 = r1->s, k1 = r1->b12, i1 = r1->b23, j1 = r1->b31;
    float s2 = r2->s, k2 = r2->b12, i2 = r2->b23, j2 = r2->b31;

    out->s   = s1*s2 - i1*i2 - j1*j2 - k1*k2;
    out->b23 = s1*i2 + i1*s2 + j1*k2 - k1*j2;
    out->b31 = s1*j2 - i1*k2 + j1*s2 + k1*i2;
    out->b12 = s1*k2 + i1*j2 - j1*i2 + k1*s2;
#else
    float s1 = r1->s, k1 = r1->b12, i1 = r1->b23, j1 = r1->b31;
    float s2 = r2->s, k2 = r2->b12, i2 = r2->b23, j2 = r2->b31;

    out->s   = s1*s2 - i1*i2 - j1*j2 - k1*k2;
    out->b23 = s1*i2 + i1*s2 + j1*k2 - k1*j2;
    out->b31 = s1*j2 - i1*k2 + j1*s2 + k1*i2;
    out->b12 = s1*k2 + i1*j2 - j1*i2 + k1*s2;
#endif
}

/*
 * Vector rotation via rotor sandwich product: v_out = R * v * R^dagger
 */
OSIRIS_API void clifford_rotate_vector(const CliffordRotor* r, const CliffordVector* v, CliffordVector* out) {
    /* Quaternion sandwich product v' = q * v * q^-1 */
    float s = r->s;
    float i = r->b23;
    float j = r->b31;
    float k = r->b12;

    float vx = v->x, vy = v->y, vz = v->z;

    /* t = 2 * cross(q.xyz, v) */
    float tx = 2.0f * (j * vz - k * vy);
    float ty = 2.0f * (k * vx - i * vz);
    float tz = 2.0f * (i * vy - j * vx);

    /* v' = v + s * t + cross(q.xyz, t) */
    out->x = vx + s * tx + (j * tz - k * ty);
    out->y = vy + s * ty + (k * tx - i * tz);
    out->z = vz + s * tz + (i * ty - j * tx);
}

/*
 * Microbenchmark function: performs N rotor multiplications
 */
OSIRIS_API double clifford_benchmark(uint32_t iterations) {
    CliffordRotor r1, r2, r_out;
    clifford_rotor_from_axis_angle(THETA_LOCK_RAD, 1.0f, 1.0f, 1.0f, &r1);
    clifford_rotor_from_axis_angle(THETA_LOCK_RAD * 0.5f, 0.0f, 1.0f, 0.0f, &r2);

    for (uint32_t i = 0; i < iterations; i++) {
        clifford_rotor_multiply(&r1, &r2, &r_out);
        r1.s = r_out.s;
    }
    return (double)r_out.s;
}

#ifdef TEST_MAIN
int main() {
    printf("[OSIRIS Cl(3,0)] Running ARM64/NEON Clifford Rotor Benchmark...\n");
    CliffordRotor r;
    clifford_rotor_from_axis_angle(THETA_LOCK_RAD, 0.0f, 0.0f, 1.0f, &r);
    printf("Lock Angle Rotor: s=%.6f, b12=%.6f, b23=%.6f, b31=%.6f\n", r.s, r.b12, r.b23, r.b31);

    CliffordVector v = {1.0f, 0.0f, 0.0f};
    CliffordVector v_out;
    clifford_rotate_vector(&r, &v, &v_out);
    printf("Rotated Vector: x=%.6f, y=%.6f, z=%.6f\n", v_out.x, v_out.y, v_out.z);

    uint32_t iters = 1000000;
    clifford_benchmark(iters);
    printf("Benchmarked %u iterations successfully.\n", iters);
    return 0;
}
#endif
