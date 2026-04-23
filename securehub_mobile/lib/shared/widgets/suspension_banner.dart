import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../core/theme/app_theme.dart';

/// Inline widget shown when a site returns a 403 suspension error.
/// Use inside the body of a site screen instead of a full-screen route
/// when you want to preserve navigation context.
class SuspensionBanner extends StatelessWidget {
  const SuspensionBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppTheme.errorContainer.withValues(alpha: 0.4),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.block_rounded,
                size: 40,
                color: AppTheme.error,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Access Suspended',
              style: GoogleFonts.inter(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                color: AppTheme.primary,
                letterSpacing: -0.3,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              'Your subscription has been suspended due to a billing issue. '
              'Please contact support to reactivate.',
              textAlign: TextAlign.center,
              style: GoogleFonts.inter(
                color: AppTheme.onSurfaceVariant,
                fontSize: 14,
                height: 1.5,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
