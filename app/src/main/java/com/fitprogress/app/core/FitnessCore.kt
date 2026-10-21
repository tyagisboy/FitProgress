package com.fitprogress.app.core

import kotlin.math.pow
import kotlin.math.roundToInt

enum class WeightUnit { KG, LBS }
enum class HeightUnit { CM, FT_IN }
enum class ExerciseType { STRENGTH, BODYWEIGHT, ASSISTED, TIMED, CARDIO }
enum class MuscleGroup { CHEST, BACK, LEGS, SHOULDERS, ARMS, CORE, CARDIO }
enum class ProgressionStatus(val label: String) {
    IMPROVING("Improving"), MAINTAINING("Maintaining"),
    POSSIBLE_DECLINE("Possible Decline"), INSUFFICIENT_DATA("Insufficient Data")
}

data class SessionDataPoint(val epochMs: Long, val dateIso: String, val value: Double, val details: String)

object FitnessMath {
    fun calculateBmi(weightKg: Double, heightCm: Double): Double? {
        if (weightKg <= 20.0 || heightCm <= 50.0) return null
        val heightM = heightCm / 100.0
        return ((weightKg / heightM.pow(2)) * 10.0).roundToInt() / 10.0
    }

    fun getBmiCategory(bmi: Double): String = when {
        bmi < 18.5 -> "Underweight"
        bmi < 25.0 -> "Normal weight"
        bmi < 30.0 -> "Overweight"
        else -> "Obese"
    }

    fun kgToLbs(kg: Double): Double = ((kg * 2.20462) * 10.0).roundToInt() / 10.0
    fun lbsToKg(lbs: Double): Double = ((lbs / 2.20462) * 10.0).roundToInt() / 10.0

    fun calculateVolume(loadKg: Double, reps: Int): Double =
        if (loadKg <= 0.0 || reps <= 0) 0.0 else ((loadKg * reps) * 10.0).roundToInt() / 10.0

    fun calculate1Rm(loadKg: Double, reps: Int): Double? {
        if (reps !in 1..12 || loadKg <= 0.0) return null
        if (reps == 1) return loadKg
        return ((loadKg / (1.0278 - (0.0278 * reps))) * 10.0).roundToInt() / 10.0
    }
}

object StepDeltaCalculator {
    fun calculateDelta(current: Int, last: Int): Int {
        if (current < 0 || last <= 0) return 0
        return if (current >= last) current - last else current
    }
    fun estimateDistanceKm(steps: Int): Double = ((steps * 0.762 / 1000.0) * 100.0).roundToInt() / 100.0
    fun estimateCalories(steps: Int): Int = (steps * 0.04).toInt()
}
