import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../../core/theme/app_theme.dart';
import '../../../core/notifications/notification_service.dart';

const _supportNumbers = ['030 824 9444', '020 374 6911', '054 366 5480'];

class HelpScreen extends ConsumerWidget {
  const HelpScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      appBar: AppBar(
        title: Text(
          'Help',
          style: GoogleFonts.inter(fontWeight: FontWeight.w800, fontSize: 17),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          children: [
            Text(
              'How can we help?',
              style: GoogleFonts.inter(
                fontSize: 32,
                fontWeight: FontWeight.w800,
                color: AppTheme.primary,
                letterSpacing: -1,
              ),
            ),
            const SizedBox(height: 8),
            const SizedBox(height: 48),
            _HelpCard(
              icon: Icons.mail_outline_rounded,
              title: 'Provider inbox',
              subtitle: 'Review billing notices and service updates',
              onTap: () => context.push('/messages'),
            ),
            const SizedBox(height: 12),
            _HelpCard(
              icon: Icons.call_outlined,
              title: 'Call support',
              subtitle: 'Speak with the control center right away',
              onTap: () => _showSupportSheet(context),
            ),
            const SizedBox(height: 12),
            _HelpCard(
              icon: Icons.lock_reset_rounded,
              title: 'Login & password help',
              subtitle: 'Get recovery guidance and contact options',
              onTap: () => _showPasswordHelp(context),
            ),
            const SizedBox(height: 12),
            _HelpCard(
              icon: Icons.notification_important_rounded,
              title: 'Test Alarm Overlay',
              subtitle: 'Preview the high-urgency alarm screen',
              onTap: () {
                ref.read(notificationServiceProvider).showTestNotification(type: 'alarm');
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Test alarm notification sent. Tap it to see the overlay.')),
                );
              },
            ),
            const SizedBox(height: 48),
            Padding(
              padding: const EdgeInsets.only(left: 4, bottom: 20),
              child: Text(
                'POPULAR TOPICS',
                style: GoogleFonts.inter(
                  fontSize: 10,
                  fontWeight: FontWeight.w800,
                  letterSpacing: 1.5,
                  color: AppTheme.onSurfaceVariant,
                ),
              ),
            ),
            Container(
              decoration: BoxDecoration(
                color: AppTheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(24),
              ),
              child: const Column(
                children: [
                  _FaqTile(
                    question: 'How do I review device health?',
                    answer:
                        'Open Devices to review sensors, hubs, battery levels and connectivity. Offline or low-battery items should be checked first.',
                  ),
                  _FaqTile(
                    question: 'What happens when an alarm is triggered?',
                    answer:
                        'You should receive a push notification, see the alert in Activity, and review any available cameras before taking action.',
                  ),
                  _FaqTile(
                    question: 'How do I switch between sites?',
                    answer:
                        'Open Profile and tap the active site card. If your account has access to more than one site, you can switch there.',
                  ),
                  _FaqTile(
                    question: 'How do I reset my password or code?',
                    answer:
                        'Password and installer-level code resets are handled by your provider or system administrator for security reasons.',
                    isLast: true,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 120),
          ],
        ),
    );
  }

  static Future<void> _showPasswordHelp(BuildContext context) async {
    HapticFeedback.lightImpact();
    await showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppTheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        title: Text(
          'Login & Password Help',
          style: GoogleFonts.inter(
            fontWeight: FontWeight.w800,
            color: AppTheme.primary,
          ),
        ),
        content: Text(
          'Password resets and installer-level code changes are handled by your provider for security reasons. If you still have access on this device, try biometric sign-in first. Otherwise call support for account recovery.',
          style: GoogleFonts.inter(
            color: AppTheme.onSurfaceVariant,
            fontSize: 14,
            height: 1.5,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              _showSupportSheet(context);
            },
            child: const Text('Call Support'),
          ),
        ],
      ),
    );
  }

  static Future<void> _showSupportSheet(BuildContext context) async {
    HapticFeedback.lightImpact();
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        decoration: const BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
        ),
        padding: const EdgeInsets.fromLTRB(24, 12, 24, 32),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppTheme.outlineVariant.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Call The Control Center',
                style: GoogleFonts.inter(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Use the fastest available number below for urgent account, alarm, or monitoring issues.',
                style: GoogleFonts.inter(
                  color: AppTheme.onSurfaceVariant,
                  fontSize: 13,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 20),
              for (final number in _supportNumbers) ...[
                _SupportNumberTile(number: number),
                const SizedBox(height: 8),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _HelpCard extends StatefulWidget {
  const _HelpCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  State<_HelpCard> createState() => _HelpCardState();
}

class _HelpCardState extends State<_HelpCard> {
  double _scale = 1.0;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _scale = 0.96),
      onTapUp: (_) => setState(() => _scale = 1.0),
      onTapCancel: () => setState(() => _scale = 1.0),
      child: AnimatedScale(
        scale: _scale,
        duration: const Duration(milliseconds: 100),
        child: Container(
          decoration: BoxDecoration(
            color: AppTheme.surfaceContainerLow,
            borderRadius: BorderRadius.circular(20),
          ),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                HapticFeedback.lightImpact();
                widget.onTap();
              },
              borderRadius: BorderRadius.circular(20),
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: const BoxDecoration(
                        color: AppTheme.surfaceContainerLowest,
                        shape: BoxShape.circle,
                      ),
                      child: Icon(
                        widget.icon,
                        color: AppTheme.primary,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            widget.title,
                            style: GoogleFonts.inter(
                              fontWeight: FontWeight.w700,
                              fontSize: 15,
                              color: AppTheme.primary,
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            widget.subtitle,
                            style: GoogleFonts.inter(
                              color: AppTheme.onSurfaceVariant,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const Icon(
                      Icons.chevron_right_rounded,
                      color: AppTheme.outlineVariant,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _FaqTile extends StatelessWidget {
  const _FaqTile({
    required this.question,
    required this.answer,
    this.isLast = false,
  });
  final String question;
  final String answer;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ExpansionTile(
          shape: const RoundedRectangleBorder(side: BorderSide.none),
          tilePadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          onExpansionChanged: (expanded) {
            if (expanded) HapticFeedback.selectionClick();
          },
          title: Text(
            question,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: AppTheme.primary,
            ),
          ),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
              child: Text(
                answer,
                style: GoogleFonts.inter(
                  color: AppTheme.onSurfaceVariant,
                  fontSize: 13,
                  height: 1.6,
                ),
              ),
            ),
          ],
        ),
        if (!isLast)
          Divider(
            height: 1,
            indent: 20,
            endIndent: 20,
            color: AppTheme.outlineVariant.withValues(alpha: 0.1),
          ),
      ],
    );
  }
}

class _SupportNumberTile extends StatelessWidget {
  const _SupportNumberTile({required this.number});

  final String number;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => launchUrl(Uri.parse('tel:${number.replaceAll(' ', '')}')),
        borderRadius: BorderRadius.circular(16),
        child: Ink(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          decoration: BoxDecoration(
            color: AppTheme.surfaceContainerLow,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.secondary.withValues(alpha: 0.08),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.phone_enabled_rounded,
                  color: AppTheme.primary,
                  size: 20,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  number,
                  style: GoogleFonts.inter(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.primary,
                    letterSpacing: 0.3,
                  ),
                ),
              ),
              const Icon(
                Icons.chevron_right_rounded,
                color: AppTheme.outlineVariant,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
