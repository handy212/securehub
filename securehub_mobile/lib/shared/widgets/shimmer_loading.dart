import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';
import '../../core/theme/app_theme.dart';

/// A simple colored box to be used as a placeholder inside a [Shimmer] widget.
class ShimmerBox extends StatelessWidget {
  const ShimmerBox({
    super.key,
    this.width,
    this.height,
    this.borderRadius = 8,
  });

  final double? width;
  final double? height;
  final double borderRadius;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: Colors.white, // The color here doesn't matter much as Shimmer overrides it
        borderRadius: BorderRadius.circular(borderRadius),
      ),
    );
  }
}

/// Legacy wrapper for backward compatibility, but prefers using [ShimmerBox] 
/// inside a single [Shimmer.fromColors] for performance.
class ShimmerLoading extends StatelessWidget {
  const ShimmerLoading({
    super.key,
    this.width,
    this.height,
    this.borderRadius = 8,
    this.child,
  });

  final double? width;
  final double? height;
  final double borderRadius;
  final Widget? child;

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppTheme.surfaceContainerHighest,
      highlightColor: AppTheme.surfaceContainerLowest,
      period: const Duration(milliseconds: 1500),
      child: child ??
          ShimmerBox(
            width: width,
            height: height,
            borderRadius: borderRadius,
          ),
    );
  }
}

class EventCardShimmer extends StatelessWidget {
  const EventCardShimmer({super.key});

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppTheme.surfaceContainerHighest,
      highlightColor: AppTheme.surfaceContainerLowest,
      period: const Duration(milliseconds: 1500),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: AppTheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Row(
          children: [
            SizedBox(width: 4),
            ShimmerBox(width: 4, height: 48, borderRadius: 16),
            SizedBox(width: 16),
            ShimmerBox(width: 44, height: 44, borderRadius: 22),
            SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ShimmerBox(width: 100, height: 12),
                  SizedBox(height: 6),
                  ShimmerBox(width: 150, height: 14),
                ],
              ),
            ),
            Padding(
              padding: EdgeInsets.only(right: 16),
              child: ShimmerBox(width: 30, height: 10),
            ),
          ],
        ),
      ),
    );
  }
}

class ZoneTileShimmer extends StatelessWidget {
  const ZoneTileShimmer({super.key});

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppTheme.surfaceContainerHighest,
      highlightColor: AppTheme.surfaceContainerLowest,
      period: const Duration(milliseconds: 1500),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: AppTheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Row(
          children: [
            ShimmerBox(width: 4, height: 48, borderRadius: 16),
            SizedBox(width: 16),
            ShimmerBox(width: 44, height: 44, borderRadius: 22),
            SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  ShimmerBox(width: 120, height: 14),
                  SizedBox(height: 6),
                  ShimmerBox(width: 60, height: 16, borderRadius: 100),
                ],
              ),
            ),
            Padding(
              padding: EdgeInsets.only(right: 16),
              child: ShimmerBox(width: 20, height: 20),
            ),
          ],
        ),
      ),
    );
  }
}
