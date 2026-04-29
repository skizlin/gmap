import math

def solve_for_odds(odds, target_overround, remove_overround, accuracy):
    """
    Calculates adjusted odds based on target overround using a logarithmic function.
    
    Parameters:
    -----------
    odds : list of float
        List of decimal odds (e.g., [2.0, 3.0, 4.0])
    target_overround : float
        Target overround as a decimal value >= 100.0 with exactly 1 decimal place (e.g., 107.0 for 7% overround)
    remove_overround : float
        Overround to remove from input odds (usually 0.0)
    accuracy : int
        Number of decimal places for calculation accuracy
    
    Returns:
    --------
    tuple: (remove_overround_result, true_odds, c, adjusted_odds)
        - remove_overround_result: Power coefficient for removing overround
        - true_odds: Odds after removing initial overround
        - c: Final power coefficient
        - adjusted_odds: Final odds after applying target overround
    """
    
    def remove_overround_fn(odds, overround, accuracy):
        """
        Helper function to remove overround from input odds using Newton-Raphson method.
        
        Parameters:
        -----------
        odds : list of float
            Input decimal odds
        overround : float
            Overround to remove
        accuracy : int
            Desired calculation accuracy
        
        Returns:
        --------
        tuple: (c, true_odds)
            - c: Power coefficient
            - true_odds: Odds after removing overround
        """
        c = 1  # Initial guess for power coefficient
        max_error = (10 ** (-accuracy)) / 2  # Maximum allowed error
        if any(o == 0 for o in odds):
            return None, []  # Return None if any odds are zero

        current_error = 1000  # Initialize with large error to ensure first iteration runs
        iteration = 0
        
        print("\nRemoving overround iterations:")
        print("Iteration | Power (c) | Error | Step Size")
        print("----------------------------------------")
        
        # Newton-Raphson iteration to find optimal power coefficient
        # The method iteratively improves the estimate of c by:
        # 1. Calculating the current error (difference from target)
        # 2. Finding how fast the error changes (derivative)
        # 3. Taking a step proportional to error/derivative
        while current_error > max_error:
            iteration += 1
            # Calculate how far we are from the target (error_function)
            # and how fast the error changes (error_derivative)
            error_function = sum((1 / o) ** c for o in odds) - 1 - overround
            error_derivative = sum((1 / o) ** c * -math.log(o) for o in odds)
            newton_step = -error_function / error_derivative  # Step size = -error/derivative
            
            # Print iteration details
            print(f"{iteration:9d} | {c:9.6f} | {current_error:9.6f} | {newton_step:9.6f}")
            
            c += newton_step
            current_error = abs(sum((1 / o) ** c for o in odds) - 1 - overround)

        # Calculate true odds by raising original odds to power c
        true_odds = [round(o ** c, 6) for o in odds]
        return c, true_odds

    # First step: Remove any existing overround from input odds
    remove_overround_result, true_odds = remove_overround_fn(odds, remove_overround, accuracy)
    
    # Second step: Apply target overround to true odds
    c = 1  # Initial guess for power coefficient
    max_error = (10 ** (-accuracy)) / 2
    current_error = 1000
    iteration = 0

    print("\nApplying target overround iterations:")
    print("Iteration | Power (c) | Error | Step Size")
    print("----------------------------------------")
    
    # Newton-Raphson iteration to find optimal power coefficient for target overround
    # Same process as above, but now working with true odds and target overround
    while current_error > max_error:
        iteration += 1
        error_function = sum((1 / o) ** c for o in true_odds) - 1 - target_overround
        error_derivative = sum((1 / o) ** c * -math.log(o) for o in true_odds)
        newton_step = -error_function / error_derivative
        
        # Print iteration details
        print(f"{iteration:9d} | {c:9.6f} | {current_error:9.6f} | {newton_step:9.6f}")
        
        c += newton_step
        current_error = abs(sum((1 / o) ** c for o in true_odds) - 1 - target_overround)

    # Calculate final adjusted odds
    adjusted_odds = [round(o ** c, 6) for o in true_odds]
    return remove_overround_result, true_odds, c, adjusted_odds

def main():
    """
    Main function to run the log function calculator from command line.
    Handles user input and displays results.
    
    Input Requirements:
    -----------------
    - Odds: Comma-separated decimal values (e.g., 2.0, 3.0, 4.0)
    - Target Overround: Value >= 100.0 with exactly 1 decimal place (e.g., 107.0)
    
    Output Format:
    -------------
    - All margins are displayed as percentages with 1 decimal place
    - Probabilities are displayed with 4 decimal places
    - Odds are displayed with 2 decimal places
    """
    print("Log Function Calculator")
    print("----------------------")
    print("This calculator adjusts betting odds to achieve a target overround.")
    print("Overround is the bookmaker's margin (e.g., 107.0 means 7% margin).")
    print("The calculation uses a logarithmic function to distribute the margin.")
    
    # Get input odds from user
    print("\nEnter decimal odds separated by commas (e.g., 2.0, 3.0, 4.0)")
    odds_input = input("Enter odds (comma-separated): ").strip()
    odds = [float(x.strip()) for x in odds_input.split(',')]
    
    # Get target overround from user with validation
    while True:
        try:
            target_overround_input = input("\nEnter target overround (100.0 or above): ").strip()
            target_overround_value = float(target_overround_input)
            
            # Validate the input
            if target_overround_value < 100:
                print("Error: Target overround must be 100.0 or above.")
                continue
                
            target_overround = (target_overround_value - 100) / 100
            break
        except ValueError:
            print("Error: Please enter a valid number (e.g., 105 or 105.0)")
    
    # Set default values
    remove_overround = 0.0  # No initial overround to remove
    accuracy = 10  # Calculation accuracy (decimal places)
    
    # Calculate results
    remove_overround_result, true_odds, c, adjusted_odds = solve_for_odds(
        odds, target_overround, remove_overround, accuracy
    )
    
    # Display results
    print("\nResults:")
    print("--------")
    print(f"Input odds: {odds}\n")
    print(f"True odds: {true_odds}\n")
    print(f"Adjusted odds: {adjusted_odds}\n")
    print(f"Power coefficient (c): {c}")
    print(f"Remove overround result: {remove_overround_result}")
    
    # Calculate and display probabilities
    input_probs = [round(1/odd, 6) for odd in odds]
    true_probs = [round(1/odd, 6) for odd in true_odds]
    adjusted_probs = [round(1/odd, 6) for odd in adjusted_odds]
    print("\nProbabilities:")
    print("-------------")
    print(f"Input probabilities: {input_probs}")
    print(f"True probabilities: {true_probs}")
    print(f"Adjusted probabilities: {adjusted_probs}")
    
    # Calculate and format margins as percentages with 1 decimal place
    input_margin = round(sum(input_probs) * 100, 1)
    true_margin = round(sum(true_probs) * 100, 1)
    adjusted_margin = round(sum(adjusted_probs) * 100, 1)
    print(f"Input margin: {input_margin}%")
    print(f"True margin: {true_margin}%")
    print(f"Adjusted margin: {adjusted_margin}%")

if __name__ == "__main__":
    main() 