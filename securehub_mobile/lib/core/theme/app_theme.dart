import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Secure Hub Design System
/// "The Digital Concierge" — warm, editorial, tonal-layered light theme.
class AppTheme {
  // ── Core Brand Tokens ──────────────────────────────────────────────────────
  static const Color primary = Color(0xFFDC2626);
  static const Color primaryContainer = Color(0xFF991B1B);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color onPrimaryContainer = Color(0xFFFFE4E6);

  // ── Surface Hierarchy (lowest → highest elevation) ─────────────────────────
  static const Color surface = Color(0xFFF2EFE8);
  static const Color surfaceContainerLowest = Color(0xFFF8F5EF);
  static const Color surfaceContainerLow = Color(0xFFEAE6DE);
  static const Color surfaceContainer = Color(0xFFE2DDD4);
  static const Color surfaceContainerHigh = Color(0xFFDAD4CA);
  static const Color surfaceContainerHighest = Color(0xFFD2CBC0);
  static const Color surfaceDim = Color(0xFFC8C1B6);

  // ── On-Surface ─────────────────────────────────────────────────────────────
  static const Color onSurface = Color(0xFF1B1C1A);
  static const Color onSurfaceVariant = Color(0xFF46464B);
  static const Color outline = Color(0xFF76777B);
  static const Color outlineVariant = Color(0xFFBBB4A9);

  // ── Secondary — "Secure / Safe" (Black) ───────────────────────────────────
  static const Color secondary = Color(0xFF1D6B57);
  static const Color secondaryContainer = Color(0xFFD7F0E7);
  static const Color onSecondary = Color(0xFFFFFFFF);
  static const Color onSecondaryContainer = Color(0xFF0F3B31);

  // ── Error — "Alarm / Alert" ────────────────────────────────────────────────
  static const Color error = Color(0xFFBA1A1A);
  static const Color errorContainer = Color(0xFFFFDAD6);
  static const Color onError = Color(0xFFFFFFFF);
  static const Color onErrorContainer = Color(0xFF93000A);
  static const Color alarmRed = Color(0xFFD42121);
  static const Color alarmOverlayBg = Color(0xFFFFE8E8);

  // ── Tertiary — "Bypassed / Warning" ───────────────────────────────────────
  static const Color tertiaryContainer = Color(0xFF411100);
  static const Color onTertiaryContainer = Color(0xFFE55E25);
  static const Color tertiaryFixed = Color(0xFFFFDBCF);

  // ── Legacy compatibility aliases ───────────────────────────────────────────
  // ignore: non_constant_identifier_names
  static const Color brandRed = primary;
  // ignore: non_constant_identifier_names
  static const Color surfaceSlate = surfaceContainer;
  // ignore: non_constant_identifier_names
  static const Color glassBorder = outlineVariant;

  // ── Ambient shadow helpers ─────────────────────────────────────────────────
  static List<BoxShadow> get cardShadow => [
    BoxShadow(
      color: onSurface.withValues(alpha: 0.04),
      blurRadius: 40,
      offset: const Offset(0, 4),
    ),
  ];

  static List<BoxShadow> get floatingShadow => [
    BoxShadow(
      color: onSurface.withValues(alpha: 0.06),
      blurRadius: 40,
      offset: const Offset(0, 8),
    ),
  ];

  // ── Light Theme ─────────────────────────────────────────────────────────────
  static ThemeData get light {
    final base = ThemeData.light(useMaterial3: true);
    return base.copyWith(
      colorScheme: const ColorScheme(
        brightness: Brightness.light,
        primary: primary,
        onPrimary: onPrimary,
        primaryContainer: primaryContainer,
        onPrimaryContainer: onPrimaryContainer,
        secondary: secondary,
        onSecondary: onSecondary,
        secondaryContainer: secondaryContainer,
        onSecondaryContainer: onSecondaryContainer,
        tertiary: Color(0xFF513127),
        onTertiary: onPrimary,
        tertiaryContainer: tertiaryContainer,
        onTertiaryContainer: onTertiaryContainer,
        error: error,
        onError: onError,
        errorContainer: errorContainer,
        onErrorContainer: onErrorContainer,
        surface: surface,
        onSurface: onSurface,
        onSurfaceVariant: onSurfaceVariant,
        outline: outline,
        outlineVariant: outlineVariant,
        shadow: onSurface,
        inverseSurface: Color(0xFF2F312F),
        onInverseSurface: Color(0xFFF2F1EE),
        inversePrimary: Color(0xFFFCA5A5),
        surfaceTint: primary,
      ),
      scaffoldBackgroundColor: surface,
      textTheme: GoogleFonts.interTextTheme(
        base.textTheme,
      ).apply(bodyColor: onSurface, displayColor: onSurface),
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        titleTextStyle: GoogleFonts.inter(
          color: primary,
          fontSize: 17,
          fontWeight: FontWeight.w800,
          letterSpacing: -0.3,
        ),
        iconTheme: const IconThemeData(color: onSurface),
      ),
      cardTheme: CardThemeData(
        color: surfaceContainerLowest,
        elevation: 0,
        shadowColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceContainerLow,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(100),
          borderSide: BorderSide.none,
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(100),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(100),
          borderSide: BorderSide.none,
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 24,
          vertical: 18,
        ),
        labelStyle: const TextStyle(color: onSurfaceVariant, fontSize: 14),
        hintStyle: const TextStyle(color: onSurfaceVariant, fontSize: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: onPrimary,
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 18),
          shape: const StadiumBorder(),
          elevation: 0,
          textStyle: GoogleFonts.inter(
            fontWeight: FontWeight.w700,
            fontSize: 16,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: primary,
          side: BorderSide(color: outlineVariant.withValues(alpha: 0.15)),
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 18),
          shape: const StadiumBorder(),
          textStyle: GoogleFonts.inter(
            fontWeight: FontWeight.w600,
            fontSize: 15,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: primary,
          textStyle: GoogleFonts.inter(
            fontWeight: FontWeight.w600,
            fontSize: 14,
          ),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: Colors.transparent,
        thickness: 0,
      ),
      listTileTheme: ListTileThemeData(
        contentPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
        iconColor: onSurfaceVariant,
        titleTextStyle: GoogleFonts.inter(
          color: onSurface,
          fontSize: 15,
          fontWeight: FontWeight.w500,
        ),
        subtitleTextStyle: GoogleFonts.inter(
          color: onSurfaceVariant,
          fontSize: 13,
        ),
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: Colors.transparent,
        elevation: 0,
        selectedItemColor: primary,
        unselectedItemColor: onSurfaceVariant,
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: secondary,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceContainerLow,
        labelStyle: GoogleFonts.inter(
          color: onSurface,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
        shape: const StadiumBorder(),
        side: BorderSide.none,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: primary,
        contentTextStyle: GoogleFonts.inter(color: onPrimary, fontSize: 14),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
    );
  }

  // ── Dark theme — Secure Hub is light-mode only ─────────────────────────
  static ThemeData get dark => light;
}
