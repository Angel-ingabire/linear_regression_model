import 'package:flutter/material.dart';

import '../services/api_service.dart';

class PredictionScreen extends StatefulWidget {
  final ApiService? apiService;

  const PredictionScreen({super.key, this.apiService});

  @override
  State<PredictionScreen> createState() => _PredictionScreenState();
}

class _PredictionScreenState extends State<PredictionScreen> {
  static const navy = Color(0xFF14264F);
  static const blue = Color(0xFF4361EE);
  static const teal = Color(0xFF009F91);
  static const violet = Color(0xFF8656D9);
  static const amber = Color(0xFFE99B24);
  static const background = Color(0xFFF3F6FC);

  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();

  int _currentStep = 0;
  String? _message;
  bool _isLoading = false;
  double? _predictionResult;
  String? _errorMessage;

  late final ApiService _apiService;

  final _year = TextEditingController();
  final _population = TextEditingController();
  final _growth = TextEditingController();
  final _age014 = TextEditingController();
  final _secondary = TextEditingController();
  final _ratio = TextEditingController();
  final _duration = TextEditingController();
  final _gdp = TextEditingController();

  String? _country;
  String? _region;
  String? _income;

  static const countries = [
    'AGO',
    'BDI',
    'BEN',
    'BFA',
    'BWA',
    'CAF',
    'CIV',
    'CMR',
    'COD',
    'COG',
    'COM',
    'CPV',
    'DJI',
    'DZA',
    'EGY',
    'ERI',
    'ETH',
    'GAB',
    'GHA',
    'GIN',
    'GMB',
    'GNB',
    'GNQ',
    'KEN',
    'LBR',
    'LSO',
    'MAR',
    'MDG',
    'MLI',
    'MOZ',
    'MRT',
    'MUS',
    'MWI',
    'NAM',
    'NER',
    'NGA',
    'RWA',
    'SEN',
    'SLE',
    'STP',
    'SWZ',
    'SYC',
    'TCD',
    'TGO',
    'TUN',
    'TZA',
    'UGA',
    'ZAF',
    'ZMB',
    'ZWE',
  ];

  static const regions = ['Middle East & North Africa', 'Sub-Saharan Africa'];

  static const incomes = [
    'High income: nonOECD',
    'Low income',
    'Lower middle income',
    'Upper middle income',
  ];

  static const titles = [
    'Country Details',
    'Demographics',
    'Education Indicators',
    'Economy & Prediction',
  ];

  static const descriptions = [
    'Select the location for your prediction.',
    'Enter population and demographic indicators.',
    'Provide information about the education system.',
    'Review your information and prepare your prediction.',
  ];

  static const stepIcons = [
    Icons.public,
    Icons.groups_rounded,
    Icons.school_rounded,
    Icons.insights_rounded,
  ];

  static const stepColors = [blue, teal, violet, amber];

  @override
  void dispose() {
    for (final controller in [
      _year,
      _population,
      _growth,
      _age014,
      _secondary,
      _ratio,
      _duration,
      _gdp,
    ]) {
      controller.dispose();
    }

    _scrollController.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _apiService = widget.apiService ?? ApiService();
  }

  void _goToStep(int step) {
    FocusScope.of(context).unfocus();

    setState(() {
      _currentStep = step;
      _message = null;
      _predictionResult = null;
      _errorMessage = null;
    });

    if (_scrollController.hasClients) {
      _scrollController.jumpTo(0);
    }
  }

  void _next() {
    FocusScope.of(context).unfocus();

    if (!_formKey.currentState!.validate()) {
      return;
    }

    if (_currentStep < 3) {
      _goToStep(_currentStep + 1);
    } else {
      _predict();
    }
  }

  void _back() {
    if (_currentStep > 0) {
      _goToStep(_currentStep - 1);
    }
  }

  Future<void> _predict() async {
    final data = <String, dynamic>{
      'year': int.parse(_year.text.trim()),
      'population': double.parse(_population.text.trim()),
      'population_growth': double.parse(_growth.text.trim()),
      'population_age_0_14': double.parse(_age014.text.trim()),
      'secondary_enrollment': double.parse(_secondary.text.trim()),
      'pupil_teacher_ratio': double.parse(_ratio.text.trim()),
      'primary_education_duration': int.parse(_duration.text.trim()),
      'gdp_per_capita': double.parse(_gdp.text.trim()),
      'country_code': _country!,
      'region': _region!,
      'income_group': _income!,
    };

    setState(() {
      _isLoading = true;
      _predictionResult = null;
      _errorMessage = null;
      _message = null;
    });

    try {
      final prediction = await _apiService.predictEnrollment(data);
      if (mounted) {
        setState(() {
          _isLoading = false;
          _predictionResult = prediction;
        });
      }
    } on ApiException catch (e) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = e.message;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage =
              'An unexpected error occurred while contacting the prediction service.';
        });
      }
    }
  }

  Widget _header() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [navy, Color(0xFF284B94), blue],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(13),
            ),
            child: const Icon(
              Icons.school_rounded,
              color: Colors.white,
              size: 26,
            ),
          ),
          const SizedBox(width: 12),
          const Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'EnrollmentIQ',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                Text(
                  'African Education Analytics',
                  style: TextStyle(color: Color(0xFFE0E9FF), fontSize: 12),
                ),
              ],
            ),
          ),
          const Icon(Icons.auto_awesome, color: Color(0xFFFFD277)),
        ],
      ),
    );
  }

  Widget _progress() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text(
              'Prediction Setup',
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: navy,
              ),
            ),
            Text(
              '${_currentStep + 1} / 4',
              style: const TextStyle(color: blue, fontWeight: FontWeight.bold),
            ),
          ],
        ),
        const SizedBox(height: 14),
        Row(
          children: List.generate(4, (index) {
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(right: index == 3 ? 0 : 6),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  height: 8,
                  decoration: BoxDecoration(
                    color: index <= _currentStep
                        ? stepColors[index]
                        : const Color(0xFFE2E8F2),
                    borderRadius: BorderRadius.circular(20),
                  ),
                ),
              ),
            );
          }),
        ),
        const SizedBox(height: 24),
        Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: stepColors[_currentStep].withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(
                stepIcons[_currentStep],
                color: stepColors[_currentStep],
                size: 28,
              ),
            ),
            const SizedBox(width: 13),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    titles[_currentStep],
                    style: const TextStyle(
                      color: navy,
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    descriptions[_currentStep],
                    style: const TextStyle(
                      color: Color(0xFF64748B),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _field({
    required String label,
    required String hint,
    required String help,
    required TextEditingController controller,
    required IconData icon,
    required Color color,
    bool integer = false,
    bool positive = false,
    double? min,
    double? max,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 19, color: color),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    fontSize: 14,
                    color: navy,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            help,
            style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
          ),
          const SizedBox(height: 9),
          TextFormField(
            controller: controller,
            keyboardType: TextInputType.numberWithOptions(
              decimal: !integer,
              signed: true,
            ),
            textInputAction: TextInputAction.next,
            scrollPadding: const EdgeInsets.only(bottom: 120),
            decoration: InputDecoration(
              hintText: 'e.g. $hint',
              filled: true,
              fillColor: const Color(0xFFF8FAFE),
              prefixIcon: Icon(icon, color: color),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: Color(0xFFDCE5F2)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: color, width: 2),
              ),
              errorBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: Colors.redAccent),
              ),
            ),
            validator: (value) {
              final text = value?.trim() ?? '';

              if (text.isEmpty) {
                return 'Please enter $label';
              }

              final number = double.tryParse(text);

              if (number == null || !number.isFinite) {
                return 'Enter a valid number';
              }

              if (integer && int.tryParse(text) == null) {
                return 'Enter a valid whole number';
              }

              if (positive && number <= 0) {
                return 'Value must be greater than zero';
              }

              if (min != null && number < min) {
                return 'Minimum allowed: $min';
              }

              if (max != null && number > max) {
                return 'Maximum allowed: $max';
              }

              return null;
            },
          ),
        ],
      ),
    );
  }

  Widget _dropdown({
    required String label,
    required String help,
    required IconData icon,
    required Color color,
    required String? value,
    required List<String> options,
    required ValueChanged<String?> onChanged,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 19),
              const SizedBox(width: 8),
              Text(
                label,
                style: const TextStyle(
                  fontSize: 14,
                  color: navy,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 5),
          Text(
            help,
            style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
          ),
          const SizedBox(height: 9),
          DropdownButtonFormField<String>(
            initialValue: value,
            isExpanded: true,
            decoration: InputDecoration(
              filled: true,
              fillColor: const Color(0xFFF8FAFE),
              prefixIcon: Icon(icon, color: color),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
            items: options.map((option) {
              return DropdownMenuItem<String>(
                value: option,
                child: Text(option, overflow: TextOverflow.ellipsis),
              );
            }).toList(),
            onChanged: onChanged,
            validator: (selected) {
              return selected == null ? 'Please select $label' : null;
            },
          ),
        ],
      ),
    );
  }

  Widget _stepFields() {
    switch (_currentStep) {
      case 0:
        return Column(
          children: [
            _dropdown(
              label: 'Country',
              help: 'Select the African country using its ISO code.',
              icon: Icons.flag_outlined,
              color: blue,
              value: _country,
              options: countries,
              onChanged: (v) => setState(() => _country = v),
            ),
            _dropdown(
              label: 'Geographic Region',
              help: 'Select the region associated with the country.',
              icon: Icons.map_outlined,
              color: teal,
              value: _region,
              options: regions,
              onChanged: (v) => setState(() => _region = v),
            ),
            _dropdown(
              label: 'Income Classification',
              help: 'Select the historical income classification.',
              icon: Icons.account_balance_wallet_outlined,
              color: violet,
              value: _income,
              options: incomes,
              onChanged: (v) => setState(() => _income = v),
            ),
          ],
        );

      case 1:
        return Column(
          children: [
            _field(
              label: 'Observation Year',
              hint: '2010',
              help: 'Historical year from 1970 to 2016.',
              controller: _year,
              icon: Icons.calendar_month_outlined,
              color: blue,
              integer: true,
              min: 1970,
              max: 2016,
            ),
            _field(
              label: 'Total Population',
              hint: '10000000',
              help: 'Total number of people, not a percentage.',
              controller: _population,
              icon: Icons.groups_outlined,
              color: teal,
              positive: true,
            ),
            _field(
              label: 'Annual Population Growth (%)',
              hint: '2.5',
              help: 'Annual population growth rate.',
              controller: _growth,
              icon: Icons.trending_up,
              color: violet,
              min: -10,
              max: 10,
            ),
            _field(
              label: 'Population Aged 0–14 (%)',
              hint: '42.0',
              help: 'Percentage of the total population aged 0–14.',
              controller: _age014,
              icon: Icons.child_care_outlined,
              color: amber,
              min: 0,
              max: 100,
            ),
          ],
        );

      case 2:
        return Column(
          children: [
            _field(
              label: 'Secondary School Enrollment (%)',
              hint: '35.0',
              help:
                  'Gross secondary enrollment rate; '
                  'values may exceed 100%.',
              controller: _secondary,
              icon: Icons.school_outlined,
              color: violet,
              min: 0,
              max: 200,
            ),
            _field(
              label: 'Pupil–Teacher Ratio',
              hint: '40',
              help: 'Average number of pupils per teacher.',
              controller: _ratio,
              icon: Icons.co_present_outlined,
              color: teal,
              positive: true,
            ),
            _field(
              label: 'Primary Education Duration (Years)',
              hint: '6',
              help:
                  'Official primary education duration, '
                  'between 4 and 7 years.',
              controller: _duration,
              icon: Icons.menu_book_outlined,
              color: blue,
              integer: true,
              min: 4,
              max: 7,
            ),
          ],
        );

      default:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _field(
              label: 'GDP Per Capita (USD)',
              hint: '800',
              help: 'Gross domestic product per person in USD.',
              controller: _gdp,
              icon: Icons.payments_outlined,
              color: amber,
              positive: true,
            ),
            const SizedBox(height: 8),
            _reviewCard(),
            if (_message != null) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFFE4F6F0),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.check_circle_outline,
                      color: Color(0xFF087B56),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _message!,
                        style: const TextStyle(
                          color: Color(0xFF087B56),
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 16),
            _resultDisplay(),
          ],
        );
    }
  }

  Widget _reviewCard() {
    return Container(
      padding: const EdgeInsets.all(17),
      decoration: BoxDecoration(
        color: const Color(0xFFEDF2FF),
        borderRadius: BorderRadius.circular(17),
        border: Border.all(color: const Color(0xFFD5DFFF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.fact_check_outlined, color: blue),
              SizedBox(width: 9),
              Text(
                'Review Your Inputs',
                style: TextStyle(
                  color: navy,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _reviewRow('Country', _country ?? 'Not selected'),
          _reviewRow('Region', _region ?? 'Not selected'),
          _reviewRow('Income group', _income ?? 'Not selected'),
          _reviewRow('Year', _year.text),
          _reviewRow('Population', _population.text),
          _reviewRow('Growth (%)', _growth.text),
          _reviewRow('Ages 0–14 (%)', _age014.text),
          _reviewRow('Secondary enrollment (%)', _secondary.text),
          _reviewRow('Pupil–teacher ratio', _ratio.text),
          _reviewRow('Primary duration (years)', _duration.text),
          _reviewRow('GDP per capita (USD)', _gdp.text),
        ],
      ),
    );
  }

  Widget _reviewRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(fontSize: 12, color: Color(0xFF536583)),
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              value.isEmpty ? 'Not entered' : value,
              textAlign: TextAlign.end,
              style: const TextStyle(
                color: navy,
                fontSize: 12,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _resultDisplay() {
    if (_isLoading) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFF3F6FC),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            const SizedBox(
              height: 20,
              width: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation(Color(0xFF4361EE)),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'Predicting enrollment rate...',
                style: const TextStyle(
                  color: Color(0xFF64748B),
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      );
    }

    if (_predictionResult != null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFE4F6F0),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.insights_rounded,
                  color: Color(0xFF087B56),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: const Text(
                    'Predicted Primary School Enrollment Rate',
                    style: TextStyle(
                      color: Color(0xFF087B56),
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${_predictionResult!.toStringAsFixed(2)}%',
              style: const TextStyle(
                color: Color(0xFF087B56),
                fontSize: 24,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Predicted gross enrollment rate. Can exceed 100% due to '
              'over-age or under-age enrollment.',
              style: TextStyle(
                color: Color(0xFF64748B),
                fontSize: 12,
              ),
            ),
          ],
        ),
      );
    }

    if (_errorMessage != null) {
      return Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFFFDECEA),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.error_outline,
              color: Color(0xFFDC2626),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                _errorMessage!,
                style: const TextStyle(
                  color: Color(0xFFDC2626),
                  fontWeight: FontWeight.w600,
                  fontSize: 14,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return const SizedBox.shrink();
  }

  Widget _bottomNavigation() {
    return Container(
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 12),
      decoration: const BoxDecoration(
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Color(0x16000000),
            blurRadius: 15,
            offset: Offset(0, -4),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Row(
          children: [
            if (_currentStep > 0) ...[
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: _back,
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Back'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: navy,
                    minimumSize: const Size.fromHeight(54),
                  ),
                ),
              ),
              const SizedBox(width: 10),
            ],
            Expanded(
              flex: 2,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _next,
                icon: _isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor: AlwaysStoppedAnimation(Colors.white),
                        ),
                      )
                    : Icon(
                        _currentStep == 3 ? Icons.auto_awesome : Icons.arrow_forward,
                      ),
                label: Text(
                  _isLoading
                      ? 'Predicting...'
                      : (_currentStep == 3 ? 'Predict Enrollment' : 'Continue'),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: stepColors[_currentStep],
                  foregroundColor: Colors.white,
                  minimumSize: const Size.fromHeight(54),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: background,
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: Column(
          children: [
            _header(),
            Expanded(
              child: Scrollbar(
                controller: _scrollController,
                thumbVisibility: true,
                thickness: 4,
                radius: const Radius.circular(10),
                child: ListView(
                  controller: _scrollController,
                  physics: const ClampingScrollPhysics(),
                  keyboardDismissBehavior:
                      ScrollViewKeyboardDismissBehavior.onDrag,
                  padding: const EdgeInsets.fromLTRB(18, 20, 18, 30),
                  children: [
                    Container(
                      padding: const EdgeInsets.all(19),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(22),
                        boxShadow: const [
                          BoxShadow(
                            color: Color(0x10000000),
                            blurRadius: 18,
                            offset: Offset(0, 5),
                          ),
                        ],
                      ),
                      child: Form(
                        key: _formKey,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            _progress(),
                            const SizedBox(height: 26),
                            _stepFields(),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    const Text(
                      'Historical prediction model • 1970–2016\n'
                      'Results are estimates, not official statistics.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Color(0xFF748198),
                        fontSize: 12,
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            _bottomNavigation(),
          ],
        ),
      ),
    );
  }
}
