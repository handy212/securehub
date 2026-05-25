import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:font_awesome_flutter/font_awesome_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../core/biometric/biometric_lock_service.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/widgets/app_backdrop.dart';
import '../../../shared/widgets/app_surfaces.dart';
import '../providers/login_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscurePassword = true;
  bool _showBiometricLogin = false;

  @override
  void initState() {
    super.initState();
    _loadBiometricAvailability();
  }

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadBiometricAvailability() async {
    final biometricService = ref.read(biometricLockServiceProvider);
    final isEnabled = await biometricService.isEnabled();

    if (!mounted) return;
    setState(() => _showBiometricLogin = isEnabled);
  }

  void _submit() {
    if (_formKey.currentState?.validate() != true) return;
    ref
        .read(loginNotifierProvider.notifier)
        .submit(_usernameCtrl.text.trim(), _passwordCtrl.text);
  }

  void _submitBiometric() {
    ref.read(loginNotifierProvider.notifier).signInWithBiometrics();
  }

  void _submitGoogle() {
    ref.read(loginNotifierProvider.notifier).signInWithGoogle();
  }

  void _showForgotPassword() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => Container(
        decoration: const BoxDecoration(
          color: AppTheme.surfaceContainerLowest,
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
                    color: AppTheme.outlineVariant.withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(100),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              Text(
                'Password Help',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'For security, password resets are handled by your provider or administrator. If you still have access on this device, you may also be able to use biometric sign-in.',
                style: TextStyle(
                  fontSize: 14,
                  color: AppTheme.onSurfaceVariant,
                  height: 1.5,
                ),
              ),
              const SizedBox(height: 24),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.support_agent_rounded,
                      color: AppTheme.primary,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Have your site name and username ready before contacting support.',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: AppTheme.onSurface,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Understood'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _showUrgentHelp() async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => Container(
        decoration: const BoxDecoration(
          color: AppTheme.surfaceContainerLowest,
          borderRadius: BorderRadius.vertical(top: Radius.circular(32)),
        ),
        padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
        child: SafeArea(
          top: false,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Center(
                child: Container(
                  width: 30,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: 24),
                  decoration: BoxDecoration(
                    color: AppTheme.outlineVariant.withValues(alpha: 0.3),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              Text(
                'Experiencing login issues?',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.primary,
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'CALL THE CONTROL CENTER (24/7)',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                  color: AppTheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 12),
              const _EmergencyPhoneTile(number: '030 824 9444'),
              const SizedBox(height: 8),
              const _EmergencyPhoneTile(number: '020 374 6911'),
              const SizedBox(height: 8),
              const _EmergencyPhoneTile(number: '054 366 5480'),
              const SizedBox(height: 32),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('Close'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final loginState = ref.watch(loginNotifierProvider);
    final isSubmitting = loginState is LoginSubmitting;

    return Scaffold(
      backgroundColor: AppTheme.surface,
      body: AppBackdrop(
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final topSpacing = constraints.maxHeight >= 820 ? 72.0 : 32.0;
              final bottomSpacing = constraints.maxHeight >= 820 ? 40.0 : 20.0;

              return SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
                child: Center(
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 460),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          ConstrainedBox(
                            constraints: BoxConstraints(
                              minHeight: (constraints.maxHeight - 56).clamp(
                                0.0,
                                double.infinity,
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                SizedBox(height: topSpacing),
                                Center(
                                  child: Column(
                                    children: [
                                      Container(
                                        width: 72,
                                        height: 72,
                                        padding: const EdgeInsets.all(16),
                                        decoration: BoxDecoration(
                                          color:
                                              AppTheme.surfaceContainerLowest,
                                          borderRadius: BorderRadius.circular(
                                            22,
                                          ),
                                          border: Border.all(
                                            color: AppTheme.outlineVariant
                                                .withValues(alpha: 0.16),
                                          ),
                                          boxShadow: AppTheme.cardShadow,
                                        ),
                                        child: Image.asset(
                                          'assets/images/Logo-WhiteBG.png',
                                          fit: BoxFit.contain,
                                        ),
                                      ),
                                      const SizedBox(height: 20),
                                      Text(
                                        'Secure Hub',
                                        style: TextStyle(
                                          fontSize: 30,
                                          fontWeight: FontWeight.w800,
                                          letterSpacing: -0.9,
                                          color: AppTheme.primary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 28),
                                AppPanel(
                                  padding: const EdgeInsets.fromLTRB(
                                    24,
                                    24,
                                    24,
                                    20,
                                  ),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.stretch,
                                    children: [
                                      const AppSectionHeader(title: 'Sign In'),
                                      if (loginState is LoginError) ...[
                                        const SizedBox(height: 18),
                                        _buildErrorCard(loginState.message),
                                      ],
                                      const SizedBox(height: 20),
                                      TextFormField(
                                        controller: _usernameCtrl,
                                        keyboardType:
                                            TextInputType.emailAddress,
                                        textInputAction: TextInputAction.next,
                                        style: TextStyle(
                                          fontWeight: FontWeight.w600,
                                        ),
                                        decoration: const InputDecoration(
                                          labelText: 'Username or Email',
                                          prefixIcon: Icon(
                                            Icons.person_outline_rounded,
                                            size: 22,
                                          ),
                                        ),
                                        validator: (v) =>
                                            (v?.trim().isEmpty ?? true)
                                            ? 'Required'
                                            : null,
                                      ),
                                      const SizedBox(height: 16),
                                      TextFormField(
                                        controller: _passwordCtrl,
                                        obscureText: _obscurePassword,
                                        textInputAction: TextInputAction.done,
                                        style: TextStyle(
                                          fontWeight: FontWeight.w600,
                                        ),
                                        onFieldSubmitted: (_) => _submit(),
                                        decoration: InputDecoration(
                                          labelText: 'Password',
                                          prefixIcon: const Icon(
                                            Icons.lock_outline_rounded,
                                            size: 22,
                                          ),
                                          suffixIcon: Row(
                                            mainAxisSize: MainAxisSize.min,
                                            children: [
                                              if (_showBiometricLogin)
                                                IconButton(
                                                  tooltip:
                                                      'Sign in with biometrics',
                                                  onPressed: isSubmitting
                                                      ? null
                                                      : _submitBiometric,
                                                  icon: const Icon(
                                                    Icons.fingerprint_rounded,
                                                    size: 21,
                                                  ),
                                                ),
                                              IconButton(
                                                icon: Icon(
                                                  _obscurePassword
                                                      ? Icons
                                                            .visibility_outlined
                                                      : Icons
                                                            .visibility_off_outlined,
                                                  size: 20,
                                                ),
                                                onPressed: () => setState(
                                                  () => _obscurePassword =
                                                      !_obscurePassword,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                        validator: (v) => (v?.isEmpty ?? true)
                                            ? 'Required'
                                            : null,
                                      ),
                                      Align(
                                        alignment: Alignment.centerRight,
                                        child: Padding(
                                          padding: const EdgeInsets.only(
                                            top: 6,
                                          ),
                                          child: TextButton(
                                            onPressed: _showForgotPassword,
                                            style: TextButton.styleFrom(
                                              foregroundColor:
                                                  AppTheme.onSurfaceVariant,
                                              textStyle: TextStyle(
                                                fontSize: 13,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                            child: const Text(
                                              'Forgot password?',
                                            ),
                                          ),
                                        ),
                                      ),
                                      const SizedBox(height: 16),
                                      SizedBox(
                                        height: 56,
                                        child: FilledButton(
                                          onPressed: isSubmitting
                                              ? null
                                              : _submit,
                                          child: isSubmitting
                                              ? const SizedBox(
                                                  height: 22,
                                                  width: 22,
                                                  child:
                                                      CircularProgressIndicator(
                                                        strokeWidth: 2,
                                                        color: Colors.white,
                                                      ),
                                                )
                                              : const Text('Sign In'),
                                        ),
                                      ),
                                      const SizedBox(height: 18),
                                      Row(
                                        children: [
                                          Expanded(
                                            child: Divider(
                                              color: AppTheme.outlineVariant
                                                  .withValues(alpha: 0.28),
                                            ),
                                          ),
                                          Padding(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 12,
                                            ),
                                            child: Text(
                                              'OR',
                                              style: TextStyle(
                                                fontSize: 11,
                                                fontWeight: FontWeight.w800,
                                                letterSpacing: 1.1,
                                                color:
                                                    AppTheme.onSurfaceVariant,
                                              ),
                                            ),
                                          ),
                                          Expanded(
                                            child: Divider(
                                              color: AppTheme.outlineVariant
                                                  .withValues(alpha: 0.28),
                                            ),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 18),
                                      SizedBox(
                                        height: 56,
                                        child: OutlinedButton(
                                          onPressed: isSubmitting
                                              ? null
                                              : _submitGoogle,
                                          style: OutlinedButton.styleFrom(
                                            backgroundColor:
                                                AppTheme.surfaceContainerLowest,
                                            foregroundColor: AppTheme.primary,
                                            side: BorderSide(
                                              color: AppTheme.outlineVariant
                                                  .withValues(alpha: 0.22),
                                            ),
                                            shape: RoundedRectangleBorder(
                                              borderRadius:
                                                  BorderRadius.circular(18),
                                            ),
                                            elevation: 0,
                                          ),
                                          child: Row(
                                            mainAxisAlignment:
                                                MainAxisAlignment.center,
                                            children: [
                                              Container(
                                                width: 28,
                                                height: 28,
                                                decoration: BoxDecoration(
                                                  color: Colors.white,
                                                  borderRadius:
                                                      BorderRadius.circular(14),
                                                  border: Border.all(
                                                    color: AppTheme
                                                        .outlineVariant
                                                        .withValues(
                                                          alpha: 0.16,
                                                        ),
                                                  ),
                                                ),
                                                child: const Center(
                                                  child: FaIcon(
                                                    FontAwesomeIcons.google,
                                                    size: 14,
                                                    color: Color(0xFF4285F4),
                                                  ),
                                                ),
                                              ),
                                              const SizedBox(width: 12),
                                              Text(
                                                'Continue with Google',
                                                style: TextStyle(
                                                  fontSize: 14,
                                                  fontWeight: FontWeight.w700,
                                                  letterSpacing: -0.1,
                                                ),
                                              ),
                                            ],
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 20),
                                Center(
                                  child: Wrap(
                                    alignment: WrapAlignment.center,
                                    crossAxisAlignment:
                                        WrapCrossAlignment.center,
                                    spacing: 4,
                                    children: [
                                      Text(
                                        'Having trouble?',
                                        style: TextStyle(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w500,
                                          color: AppTheme.onSurfaceVariant,
                                        ),
                                      ),
                                      TextButton(
                                        onPressed: _showUrgentHelp,
                                        style: TextButton.styleFrom(
                                          foregroundColor: AppTheme.error,
                                          textStyle: TextStyle(
                                            fontSize: 13,
                                            fontWeight: FontWeight.w700,
                                          ),
                                        ),
                                        child: const Text('Get help'),
                                      ),
                                    ],
                                  ),
                                ),
                                SizedBox(height: bottomSpacing),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildErrorCard(String message) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.error.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.error_outline_rounded,
            color: AppTheme.error,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              message,
              style: TextStyle(
                color: AppTheme.error,
                fontSize: 13,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmergencyPhoneTile extends StatelessWidget {
  const _EmergencyPhoneTile({required this.number});
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
            color: AppTheme.error.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: AppTheme.error.withValues(alpha: 0.1)),
          ),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppTheme.error.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.phone_enabled_rounded,
                  color: AppTheme.error,
                  size: 20,
                ),
              ),
              const SizedBox(width: 16),
              Text(
                number,
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.error,
                  letterSpacing: 0.5,
                ),
              ),
              const Spacer(),
              const Icon(Icons.chevron_right_rounded, color: AppTheme.error),
            ],
          ),
        ),
      ),
    );
  }
}


