// Classify Tenants — canonical data source for the whole workflow.
// Reads COI Policy Data + Alert Log, decides action per tenant, builds
// pre-rendered email subject + body ready to hand to the Gmail node.
//
// 2026-06-01: renderTemplate() refreshed with Altmark's approved
// template copy. Six branches (Initial/Followup/Final × Approaching/
// Already-Expired). All other logic, safety flags, and cadence
// decisions are unchanged.

// ========================================================================
//  SAFETY FLAGS — DEFAULT STATE IS SAFE, BOTH MUST BE FLIPPED FOR PRODUCTION
// ========================================================================
//  DRY_RUN = true (default):
//    - Every tenant email routes to DRY_RUN_REDIRECT (not real tenant)
//    - Subject prefixed "[DRY RUN -> original@tenant.com]"
//    - Body has "*** DRY RUN ***" banner
//    - Summary routes to DRY_RUN_REDIRECT
//    - Alert Log IS written, with `source` suffixed `_dry_run` so test
//      rows are easy to find and clear before going live
//  DRY_RUN = false:
//    - Tenant emails go to the real address from the spreadsheet
//    - Alert Log `source` is plain `scheduled` / `backlog` (no suffix)
//
//  ALLOW_PRODUCTION_CC = false (default):
//    - CC on tenant emails is empty (Yair/Matt never copied)
//    - Summary email goes to DRY_RUN_REDIRECT (not yair@/matt@)
//  ALLOW_PRODUCTION_CC = true:
//    - CC every tenant email to CC_PRODUCTION (Yair/Matt copied)
//    - Summary email goes to yair@/matt@
//    - Works regardless of DRY_RUN: lets Yair/Matt review dry-run drafts
//      before go-live, and receive live copies after go-live.
//
//  The two flags are now orthogonal:
//    DRY_RUN              controls whether tenant emails reach real tenants
//    ALLOW_PRODUCTION_CC  controls whether Yair/Matt receive CC + summary
//
//  Go-live: flip DRY_RUN to false. ALLOW_PRODUCTION_CC can be flipped at
//  any time independently.
const DRY_RUN = false;
const ALLOW_PRODUCTION_CC = true;
const DRY_RUN_REDIRECT = 'jtsomwaru@gmail.com';
// ========================================================================

const CC_PRODUCTION = 'yair@altmarkgroup.com,matt@altmarkgroup.com';
const SUMMARY_TO_PRODUCTION = 'yair@altmarkgroup.com,matt@altmarkgroup.com';

// ========================================================================
//  EMAIL TEMPLATE CONFIG — edit these to change content.
// ========================================================================
//  CERT_HOLDER_MAILING_ADDRESS: address that goes under the entity name in
//  the "Certificate Holder listed as:" block of Initial Request emails.
//  Confirmed with Yair on 2026-04-27 as Altmark's central intake address.
//  If per-entity mailing addresses are ever needed, add a Mailing Address
//  column to COI Policy Data and switch this to a per-row read.
const CERT_HOLDER_MAILING_ADDRESS = '2447 Third Ave, Bronx, NY 10451';
const COI_INTAKE_EMAIL = 'insurance@altmarkgroup.com';
// ========================================================================

const policyRows = $('Read COI Policy Data').all();
const logRows = $('Read Alert Log').all();

const licenseEntities = [
  'Markland 486 LLC',
  'Markland 713 LLC',
  'Bronx Canvas LLC',
  'Bronx Canvas Canal LLC'
];

const today = new Date();
today.setHours(0, 0, 0, 0);
const msPerDay = 1000 * 60 * 60 * 24;
const pad = function (n) { return n < 10 ? '0' + n : '' + n; };
const todayISO = today.getFullYear() + '-' + pad(today.getMonth() + 1) + '-' + pad(today.getDate());

// Parse YYYY-MM-DD as LOCAL midnight (avoids UTC off-by-one in ET timezone).
function parseLocalDate(raw) {
  if (raw == null || raw === '') return null;
  const s = String(raw).trim();
  const m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})/);
  if (m) return new Date(parseInt(m[1], 10), parseInt(m[2], 10) - 1, parseInt(m[3], 10));
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

const logByKey = {};
for (const row of logRows) {
  const d = row.json || {};
  if (!d.tenant_name) continue;
  const key = (d.tenant_name || '') + '|' + (d.entity_name || '');
  if (!logByKey[key]) logByKey[key] = [];
  logByKey[key].push({
    stage: d.escalation_stage,
    date_sent: d.date_sent,
    source: d.source,
    expiration_date: d.expiration_date
  });
}

function fmtExpDate(d) {
  const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  return months[d.getMonth()] + ' ' + d.getDate() + ', ' + d.getFullYear();
}

function htmlEscape(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildSignature(entityName) {
  const safeEntity = htmlEscape(entityName || 'The Altmark Group');
  return '<p>Thank you,<br>' + safeEntity + '</p>';
}

function renderTemplate(stage, ctx) {
  const addrRaw = ctx.property_address || '';
  const unitRaw = ctx.unit || 'Single Tenant';
  const addr = htmlEscape(addrRaw);
  const unit = htmlEscape(unitRaw);
  const tenant = htmlEscape(ctx.tenant_name);
  const entity = htmlEscape(ctx.entity_name);
  const mailingAddr = htmlEscape(CERT_HOLDER_MAILING_ADDRESS);
  const intakeEmail = htmlEscape(COI_INTAKE_EMAIL);
  const intakeMailto = '<a href="mailto:' + intakeEmail + '">' + intakeEmail + '</a>';
  const leaseLic = htmlEscape(ctx.lease_or_license);
  const expNice = htmlEscape(ctx.expiration_nice || '');
  const expNiceRaw = ctx.expiration_nice || '';
  // approaching = COI is still valid (not yet expired). These tenants get
  // renewal-reminder wording; already-expired tenants get current-coverage
  // wording with an explicit "do not just resend the old expired
  // certificate" guard (per Altmark template refresh 2026-06-01).
  // Day-0 never reaches here (it is escalation_needed).
  const approaching = (typeof ctx.days_until_expiration === 'number' && ctx.days_until_expiration > 0);

  // Cert-requirements bullet list shared by both Initial Request templates.
  // firstBulletText lets Template 2 (Already Expired) emphasize "with an
  // active policy period" on the General Liability bullet.
  function buildRequirements(firstBulletText) {
    return (
      '<ul>' +
        '<li>' + firstBulletText + '</li>' +
        '<li>Property address listed as: ' + addr + '</li>' +
        '<li>Landlord / ownership entity listed as Additional Insured</li>' +
        '<li>Certificate Holder listed as:' +
          '<div style="margin-top:8px;margin-left:0;">' +
            entity + '<br>' +
            mailingAddr +
          '</div>' +
        '</li>' +
      '</ul>'
    );
  }

  if (stage === 'initial_request') {
    if (approaching) {
      // Template 1: Initial Request (Approaching Expiration)
      return {
        subject: 'Renewal Certificate of Insurance Needed for ' + addrRaw + ' \u2013 Expires ' + expNiceRaw,
        body:
          '<p>Hi ' + tenant + ',</p>' +
          '<p>I hope you are doing well.</p>' +
          '<p>Your current Certificate of Insurance for ' + addr + ' is on file with us and is set to expire on ' + expNice + '. We are reaching out now so there is time to get the renewal certificate in place before the current one lapses.</p>' +
          '<p>Please have your insurance agent issue the renewal COI for the upcoming policy period and send it to us. It should include:</p>' +
          buildRequirements('General Liability coverage') +
          '<p>Your insurance agent can email it directly to ' + intakeMailto + '.</p>' +
          '<p>We need the renewal certificate on file before ' + expNice + '. If your agent has already issued it for the new policy period and it is on the way, just let us know.</p>' +
          buildSignature(ctx.entity_name)
      };
    }
    // Template 2: Initial Request (Already Expired)
    return {
      subject: 'Current Certificate of Insurance Needed for ' + addrRaw + ' \u2013 Prior Policy Expired',
      body:
        '<p>Hi ' + tenant + ',</p>' +
        '<p>I hope you are doing well.</p>' +
        '<p>The most recent Certificate of Insurance we have on file for ' + addr + ' has already expired, so we do not have active coverage documentation for your space. We need a certificate showing a current, in-force policy \u2014 meaning the policy period must cover today\'s date and going forward.</p>' +
        '<p>Please have your insurance agent issue a current COI and send it to us. It should include:</p>' +
        buildRequirements('General Liability coverage with an active policy period') +
        '<p>Your insurance agent can email it directly to ' + intakeMailto + '.</p>' +
        '<p>Please note: resending the previously issued certificate will not resolve this \u2014 the policy on that certificate has expired. We need the new certificate for your current policy period.</p>' +
        '<p>If you have already had your agent issue a current certificate and it is on the way, please let us know.</p>' +
        buildSignature(ctx.entity_name)
    };
  }
  if (stage === 'second_followup') {
    if (approaching) {
      // Template 3: Follow Up (Approaching Expiration)
      return {
        subject: 'Second Request \u2013 Renewal Certificate of Insurance Needed for ' + addrRaw,
        body:
          '<p>Hi ' + tenant + ',</p>' +
          '<p>Following up on our earlier note: your current Certificate of Insurance for ' + addr + ' expires on ' + expNice + ', and we have not yet received the renewal certificate for the new policy period.</p>' +
          '<p>To avoid a gap in your file, please have your insurance agent send the renewal COI to ' + intakeMailto + ' before the expiration date. If a broker or agent handles this for you, feel free to forward this email to them and copy us.</p>' +
          '<p>If the renewal has already been issued and is on the way, please let us know.</p>' +
          buildSignature(ctx.entity_name)
      };
    }
    // Template 4: Follow Up (Already Expired)
    return {
      subject: 'Second Request \u2013 Current Certificate of Insurance Needed for ' + addrRaw,
      body:
        '<p>Hi ' + tenant + ',</p>' +
        '<p>Following up on our earlier request: we still do not have a Certificate of Insurance on file showing a current, in-force policy for your space at ' + addr + '. The most recent certificate we have has expired.</p>' +
        '<p>Please have your insurance agent send a COI for your current policy period to ' + intakeMailto + '. If a broker or agent handles this for you, feel free to forward this email to them and copy us.</p>' +
        '<p>Please note: the previously issued certificate on file has expired, so resending that one will not resolve this. We need the certificate for the new/current policy period.</p>' +
        buildSignature(ctx.entity_name)
    };
  }
  if (stage === 'final_notice') {
    if (approaching) {
      // Template 5: Final Notice (Approaching Expiration)
      return {
        subject: 'Urgent \u2013 Renewal Certificate of Insurance Needed for ' + addrRaw + ' Before ' + expNiceRaw,
        body:
          '<p>Hi ' + tenant + ',</p>' +
          '<p>This is an urgent reminder that your Certificate of Insurance for ' + addr + ' expires on ' + expNice + ', and we have not yet received the renewal certificate for the upcoming policy period.</p>' +
          '<p>Please have your insurance agent send the renewal COI to ' + intakeMailto + ' as soon as possible to prevent a lapse in your file. Maintaining current insurance documentation is a requirement of your ' + leaseLic + '.</p>' +
          '<p>If the renewal has already been issued and is on the way, please let us know.</p>' +
          buildSignature(ctx.entity_name)
      };
    }
    // Template 6: Final Notice (Already Expired)
    return {
      subject: 'Urgent \u2013 Current Certificate of Insurance Required for ' + addrRaw,
      body:
        '<p>Hi ' + tenant + ',</p>' +
        '<p>We are again following up regarding the Certificate of Insurance required for your tenancy at ' + addr + '. The most recent certificate on file has expired, and we still do not have documentation of a current, in-force policy for your space.</p>' +
        '<p>Please provide a COI for your current policy period immediately. Failure to maintain and provide the required insurance documentation may constitute a ' + leaseLic + ' compliance issue.</p>' +
        '<p>Send the certificate to ' + intakeMailto + ' as soon as possible.</p>' +
        '<p>Please note: resending the expired certificate will not resolve this \u2014 we need the new one covering your current policy period.</p>' +
        buildSignature(ctx.entity_name)
    };
  }
  return { subject: '', body: '' };
}

const results = [];

for (const row of policyRows) {
  try {
  const d = row.json || {};
  const entityName = (d['Entity Name'] || '').toString().trim();
  const propertyAddress = (d['Property Address'] || '').toString().trim();
  const unit = (d['Unit'] || '').toString().trim();
  const tenantName = (d['Tenant Name'] || '').toString().trim();
  const email1 = (d['Tenant Email #1'] || '').toString().trim();
  const email2 = (d['Tenant Email #2'] || '').toString().trim();
  const certReceived = (d['Certificate Received'] || '').toString().trim();
  const expirationRaw = d['COI Expiration Date'];

  const base = {
    entity_name: entityName,
    property_address: propertyAddress,
    unit: unit,
    tenant_name: tenantName,
    tenant_email_1: email1,
    tenant_email_2: email2,
    certificate_received: certReceived,
    expiration_raw: expirationRaw == null ? '' : String(expirationRaw),
    today: todayISO
  };

  if (certReceived === 'Vacant' || certReceived === 'Not Required') {
    results.push(Object.assign({}, base, { action: 'skip_vacant', reason: 'certificate_received=' + certReceived }));
    continue;
  }
  if (!tenantName || tenantName === 'Vacant') {
    results.push(Object.assign({}, base, { action: 'skip_vacant', reason: 'tenant_name_blank_or_vacant' }));
    continue;
  }
  if (!email1 && !email2) {
    results.push(Object.assign({}, base, { action: 'skip_no_email' }));
    continue;
  }

  let expDate = parseLocalDate(expirationRaw);
  const minDate = new Date(2020, 0, 1);
  if (!expDate || expDate < minDate) {
    results.push(Object.assign({}, base, { action: 'skip_bad_date', expiration_display: base.expiration_raw }));
    continue;
  }

  expDate.setHours(0, 0, 0, 0);
  const daysUntilExpiration = Math.round((expDate.getTime() - today.getTime()) / msPerDay);
  const leaseOrLicense = licenseEntities.indexOf(entityName) !== -1 ? 'license agreement' : 'lease';
  const sendTo = email1 || email2;
  const expirationDisplay = expDate.getFullYear() + '-' + pad(expDate.getMonth() + 1) + '-' + pad(expDate.getDate());
  const expirationNice = fmtExpDate(expDate);

  const coreFields = Object.assign({}, base, {
    days_until_expiration: daysUntilExpiration,
    lease_or_license: leaseOrLicense,
    send_to: sendTo,
    expiration_display: expirationDisplay,
    expiration_nice: expirationNice
  });

  const key = tenantName + '|' + entityName;
  const logHistory = logByKey[key] || [];

  let outcome;

  if (daysUntilExpiration === 0) {
    // Day 0 — expiration today. No tenant email; internal alert only.
    outcome = { action: 'escalation_needed', stage: 'escalation_needed', days_since_final_notice: 0, reason: 'expires_today' };
  } else {
    // ----------------------------------------------------------------
    //  Per-cycle log filter
    // ----------------------------------------------------------------
    //  Only consider log entries whose expiration_date matches the
    //  tenant's current expiration_date. When a tenant renews and a new
    //  expiration is entered in COI Policy Data, prior-cycle log rows
    //  fall out of cycleHistory and the cascade restarts cleanly.
    const cycleHistory = logHistory.filter(function (e) {
      const d = parseLocalDate(e.expiration_date);
      if (!d) return false;
      const k = d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
      return k === expirationDisplay;
    });

    function latestEntry(stage) {
      let latest = null;
      let latestDate = null;
      for (const e of cycleHistory) {
        if (e.stage !== stage) continue;
        const d = parseLocalDate(e.date_sent);
        if (!d) continue;
        if (!latestDate || d > latestDate) { latest = e; latestDate = d; }
      }
      return latest;
    }
    function daysSince(entry) {
      const d = parseLocalDate(entry.date_sent);
      if (!d) return 0;
      d.setHours(0, 0, 0, 0);
      return Math.round((today.getTime() - d.getTime()) / msPerDay);
    }

    const initialEntry = latestEntry('initial_request');
    const followupEntry = latestEntry('second_followup');
    const finalEntry = latestEntry('final_notice');
    const sourceLabel = daysUntilExpiration > 0 ? 'scheduled' : 'backlog';

    // ----------------------------------------------------------------
    //  Cascade state machine
    // ----------------------------------------------------------------
    //  Each transition gated on BOTH a time-since-last-email check AND a
    //  deadline-proximity check. Time gate prevents back-to-back sends;
    //  deadline gate keeps the original 60/30/7 cadence intent.
    //
    //    nothing  -> initial_request   : daysUntilExpiration <= 60
    //    initial  -> second_followup   : daysSinceInitial >= 14  AND  daysUntilExpiration <= 30
    //    followup -> final_notice      : daysSinceFollowup >= 7  AND  daysUntilExpiration <= 7
    //    final    -> escalation_needed : daysSinceFinal >= 7
    //
    //  Always advances at most one stage per run, in order — a tenant
    //  never receives "Second Request" without first receiving an
    //  initial_request, so the body language stays coherent.
    if (finalEntry) {
      const daysSinceFinal = daysSince(finalEntry);
      if (daysSinceFinal >= 7) {
        outcome = { action: 'escalation_needed', stage: 'escalation_needed', days_since_final_notice: daysSinceFinal };
      } else {
        outcome = { action: 'no_action', reason: 'waiting_after_final_notice' };
      }
    } else if (followupEntry) {
      const daysSinceFollowup = daysSince(followupEntry);
      if (daysSinceFollowup >= 7 && daysUntilExpiration <= 7) {
        outcome = { action: 'send_email', stage: 'final_notice', source: sourceLabel };
      } else {
        outcome = { action: 'no_action', reason: 'waiting_for_final_notice' };
      }
    } else if (initialEntry) {
      const daysSinceInitial = daysSince(initialEntry);
      // Faster cadence once expired (per Yair/Matt 2026-04-28): 7 days from
      // initial to second_followup if the COI is already past expiration.
      // Tenants whose COI is still valid keep the 14-day gap so the
      // scheduled-path cadence (initial at day 60, followup at day 30)
      // remains intact.
      const initialGate = daysUntilExpiration <= 0 ? 7 : 14;
      if (daysSinceInitial >= initialGate && daysUntilExpiration <= 30) {
        outcome = { action: 'send_email', stage: 'second_followup', source: sourceLabel };
      } else {
        outcome = { action: 'no_action', reason: 'waiting_for_second_followup' };
      }
    } else {
      if (daysUntilExpiration <= 60) {
        outcome = { action: 'send_email', stage: 'initial_request', source: sourceLabel };
      } else {
        outcome = { action: 'compliant' };
      }
    }
  }

  const merged = Object.assign({}, coreFields, outcome);
  merged.is_dry_run = DRY_RUN;
  merged.allow_production_cc = ALLOW_PRODUCTION_CC;

  if (merged.action === 'send_email') {
    const tpl = renderTemplate(merged.stage, merged);
    const originalTo = merged.send_to;
    // CC depends only on ALLOW_PRODUCTION_CC and is the same in both modes.
    merged.cc_list = ALLOW_PRODUCTION_CC ? CC_PRODUCTION : '';
    if (DRY_RUN) {
      merged.send_to = DRY_RUN_REDIRECT;
      merged.email_subject = '[DRY RUN -> ' + originalTo + '] ' + tpl.subject;
      merged.email_body =
        '<div style="background:#fff3cd;border-left:4px solid #ffc107;padding:12px;margin-bottom:16px;font-family:monospace;">' +
          '<strong>*** DRY RUN MODE ***</strong><br>' +
          'This email would have been sent to <strong>' + htmlEscape(originalTo) + '</strong>.<br>' +
          'Flip <code>DRY_RUN</code> to <code>false</code> in Classify Tenants to go live.' +
        '</div>' +
        tpl.body;
    } else {
      merged.email_subject = tpl.subject;
      merged.email_body = tpl.body;
    }
  }

  results.push(merged);
  } catch (err) {
    // Single-row failure: emit a workflow_error item so the rest of the
    // batch continues. The row appears in Build Daily Summary's Data
    // Issues section and the global Error Trigger does NOT fire (we
    // handled it). Top-level failures (Sheets credential expired, etc.)
    // bypass this catch and bubble up to the error notifier as designed.
    const d = row.json || {};
    results.push({
      action: 'workflow_error',
      error_message: (err && err.message) || String(err),
      tenant_name: ((d['Tenant Name'] || '').toString().trim()) || '(unknown)',
      entity_name: (d['Entity Name'] || '').toString().trim(),
      property_address: (d['Property Address'] || '').toString().trim(),
      unit: (d['Unit'] || '').toString().trim()
    });
  }
}

return results.map(function (r) { return { json: r }; });
