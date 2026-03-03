"use client";

import { TextField, TextFieldProps } from "@mui/material";
import { useState, useEffect } from "react";

interface FormattedNumberInputProps extends Omit<TextFieldProps, "value" | "onChange"> {
  value: string;
  onChange: (value: string) => void;
  decimals?: number;
  allowNegative?: boolean;
}

export function FormattedNumberInput({
  value,
  onChange,
  decimals = 0,
  allowNegative = false,
  ...textFieldProps
}: FormattedNumberInputProps) {
  const [displayValue, setDisplayValue] = useState("");
  const [isFocused, setIsFocused] = useState(false);

  // Sync internal state when external value changes
  useEffect(() => {
    if (!isFocused) {
      const num = parseFloat(value);
      if (isNaN(num) || (num === 0 && value === "")) {
        setDisplayValue("");
      } else {
        setDisplayValue(num.toFixed(decimals));
      }
    }
  }, [value, decimals, isFocused]);

  const handleFocus = () => {
    setIsFocused(true);
    // Show raw number on focus for easy editing
    const num = parseFloat(value);
    if (isNaN(num) || (num === 0 && value === "")) {
      setDisplayValue("");
    } else {
      setDisplayValue(num.toString());
    }
  };

  const handleBlur = () => {
    setIsFocused(false);
    // Keep raw number format (dot as decimal) - MT5 style
    if (displayValue === "") {
      onChange("");
      setDisplayValue("");
    } else {
      const num = parseFloat(displayValue);
      if (!isNaN(num)) {
        const formatted = num.toFixed(decimals);
        onChange(formatted);
        setDisplayValue(formatted);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target.value;
    // Validation regex: allow digits, optional decimal point, optional minus sign
    const regex = allowNegative ? /^-?\d*\.?\d*$/ : /^\d*\.?\d*$/;

    if (input === "" || regex.test(input)) {
      setDisplayValue(input);
      if (isFocused) {
        onChange(input);
      }
    }
  };

  return (
    <TextField
      {...textFieldProps}
      value={displayValue}
      onChange={handleChange}
      onFocus={handleFocus}
      onBlur={handleBlur}
    />
  );
}
