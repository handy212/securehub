import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/auth/auth_notifier.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_backdrop.dart';

const _supportNumbers = ['030 824 9444', '020 374 6911', '054 366 5480'];

class AccountSuspendedScreen extends ConsumerWidget {
  const AccountSuspendedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: AppBackdrop(
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(40),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Identity Icon
                  Container(
                    width: 100,
                    height: 100,
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceContainerLowest,
                      shape: BoxShape.circle,
                      boxShadow: AppTheme.cardShadow,
                      border: Border.all(
                        color: AppTheme.outlineVariant.withValues(alpha: 0.1),
                      ),
                    ),
                    child: Image.asset(
                      'assets/images/Logo-WhiteBG.png',
                      fit: BoxFit.contain,
                    ),
                  ),
                  const SizedBox(height: 48),
                  
                  Text(
                    'SYSTEM ALERT',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.error,
                      letterSpacing: 2,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Account Suspended',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      color: AppTheme.primary,
                      letterSpacing: -0.5,
                    ),
                  ),
                  const SizedBox(height: 32),
                  
                  Container(
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      color: AppTheme.surfaceContainerLow,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: Text(
                      'Your security monitoring has been temporarily suspended due to an outstanding balance on your account.\n\nTo restore immediate protection and access to your sites, please contact your service provider to settle any overdue payments.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: AppTheme.onSurfaceVariant,
                        fontSize: 15,
                        height: 1.6,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  const SizedBox(height: 56),
                  
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: () => _showSupportSheet(context),
                      child: const Text('Contact Support'),
                    ),
                  ),
                  const SizedBox(height: 12),

                  SizedBox(
                    width: double.infinity,
                    child: OutlinedButton(
                      onPressed: () =>
                          ref.read(authNotifierProvider.notifier).logout(),
                      child: const Text('Log Out'),
                    ),
                  ),
                  const SizedBox(height: 32),
                  Text(
                    'SECURE HUB',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: AppTheme.outlineVariant,
                      letterSpacing: 2,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _showSupportSheet(BuildContext context) async {
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
                'Restore Service',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Contact your provider or control center using the numbers below to settle the account and restore monitoring access.',
                style: TextStyle(
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
                  color: AppTheme.error.withValues(alpha: 0.08),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.phone_enabled_rounded,
                  color: AppTheme.error,
                  size: 20,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Text(
                  number,
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.w800,
                    color: AppTheme.primary,
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

