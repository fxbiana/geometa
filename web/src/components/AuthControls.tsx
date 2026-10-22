/**
 * Auth UI stubs. After Node >= 20.9 and Clerk init, replace these with:
 *
 *   import { SignInButton, SignUpButton, UserButton, Show } from "@clerk/nextjs";
 *
 * Then wrap signed-in / signed-out branches with <Show when="signed-in"> / <Show when="signed-out">
 * (or the Clerk pattern current for your SDK version).
 */

export function AuthControls() {
  return (
    <div className="auth-controls" aria-label="Account (Clerk pending)">
      {/* <Show when="signed-out"> */}
      <SignInButtonStub />
      <SignUpButtonStub />
      {/* </Show> */}
      {/* <Show when="signed-in"> */}
      <UserButtonStub />
      {/* </Show> */}
    </div>
  );
}

/** Stub for Clerk <SignInButton /> */
function SignInButtonStub() {
  return (
    <button type="button" className="auth-btn" disabled title="Requires Clerk">
      Sign in
    </button>
  );
}

/** Stub for Clerk <SignUpButton /> */
function SignUpButtonStub() {
  return (
    <button type="button" className="auth-btn" disabled title="Requires Clerk">
      Sign up
    </button>
  );
}

/** Stub for Clerk <UserButton /> */
function UserButtonStub() {
  return (
    <span className="auth-user-stub" title="Requires Clerk">
      User
    </span>
  );
}
