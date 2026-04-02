"use client";

import React, { useEffect } from "react";
import "./SmartScheduler.css";
import { addDaysISO, dayHeaderLabel } from "./utils";

import Sidebar from "./components/Sidebar";
import MonthNavigation from "./components/MonthNavigation";
import FilterBar from "./components/FilterBar";
import MonthGrid from "./components/MonthGrid";
import DayView from "./components/DayView";
import HotkeysModal from "./components/Modals/HotkeysModal";
import ChatModal from "./components/Modals/ChatModal/ChatModal";
import { useChatModal } from "./components/Modals/ChatModal/useChatModal";
import EventModal from "./components/Modals/EventModal";

import { useEvents } from "./hooks/useEvents";
import { useFilters } from "./hooks/useFilters";
import { useCalendarView } from "./hooks/useCalendarView";
import { useEventModal } from "./hooks/useEventModal";
import { useHotkeys } from "./hooks/useHotkeys";

export default function Home() {
  const { events, addEvent, loading, error, refetch } = useEvents();
  const filters = useFilters(events);
  const calendarView = useCalendarView(filters.filteredEvents);
  const eventModal = useEventModal();
  const chat = useChatModal();
  const hotkeys = useHotkeys(eventModal.setOpen, chat); // placeholder for setHotkeysOpen

  const { chatOpen, activeSession, isTyping, chatEndRef, isRecording, toggleRecording } = chat;

  // Refetch events when month changes
  useEffect(() => {
    const firstOfMonth = new Date(calendarView.viewYear, calendarView.viewMonth, 1);
    // Get last day of month + buffer for adjacent days shown in calendar
    const lastOfMonth = new Date(calendarView.viewYear, calendarView.viewMonth + 1, 7);
    // Also get buffer for previous month days shown
    firstOfMonth.setDate(firstOfMonth.getDate() - 7);
    
    refetch(firstOfMonth, lastOfMonth);
  }, [calendarView.viewYear, calendarView.viewMonth, refetch]);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatOpen) {
      chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [activeSession?.messages, isTyping, chatOpen, chatEndRef]);

  async function saveEvent(e: React.FormEvent) {
    e.preventDefault();

    const result = await addEvent(
      eventModal.modalKind,
      eventModal.mTitle,
      eventModal.mDate,
      eventModal.mStart,
      eventModal.mEnd,
      eventModal.mAllDay,
      eventModal.mColor,
      eventModal.mLocation,
      eventModal.mNotes,
      eventModal.realTodayKey,
      eventModal.isTodaySelected
    );

    if (!result.success) {
      alert(result.error);
      return;
    }

    eventModal.setOpen(false);
  }

  // Loading state
  if (loading && Object.keys(events).length === 0) {
    return (
      <div className="container-fluid vh-100 d-flex align-items-center justify-content-center bg-dark">
        <div className="text-center text-white">
          <div className="spinner-border text-primary mb-3" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mb-0">Loading calendar...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && Object.keys(events).length === 0) {
    return (
      <div className="container-fluid vh-100 d-flex align-items-center justify-content-center bg-dark">
        <div className="text-center text-white">
          <div className="alert alert-danger" role="alert">
            <h5 className="alert-heading">Failed to load calendar</h5>
            <p className="mb-0">{error}</p>
            <hr />
            <button 
              className="btn btn-outline-danger"
              onClick={() => refetch()}
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container-fluid vh-100 p-0 d-flex flex-column overflow-hidden bg-dark">
      <div className="flex-grow-1 d-flex overflow-hidden">
        {/* SIDEBAR */}
        <Sidebar
          today={calendarView.TODAY}
          todayMonthYear={calendarView.todayMonthYear}
          todayWeekday={calendarView.todayWeekday}
          upcoming={calendarView.upcoming}
          onHotkeysClick={() => hotkeys.setHotkeysOpen(true)}
          onChatClick={() => chat.setChatOpen(true)}
          onProfileClick={() => { }}
          onLogoClick={calendarView.goToToday}
          onEventClick={(dateKey) => {
            calendarView.setSelectedDay(dateKey);
            calendarView.setViewMode("day");
          }}
        />

        {/* MAIN */}
        <main className="flex-grow-1 d-flex flex-column bg-white text-dark overflow-hidden">
          {/* SHARED HEADER */}
          <div className="d-flex align-items-center justify-content-between px-3 border-bottom border-light-subtle bg-white" style={{ minHeight: 60 }}>
            {/* Left: Navigation */}
            {calendarView.viewMode === "month" ? (
              <MonthNavigation
                onPrev={calendarView.prevMonth}
                onNext={calendarView.nextMonth}
                title={calendarView.monthTitle}
              />
            ) : (
              <div className="d-flex align-items-center gap-3">
                <button
                  className="btn btn-outline-secondary btn-sm rounded-circle d-flex align-items-center justify-content-center shadow-sm"
                  style={{ width: 32, height: 32 }}
                  onClick={() => calendarView.setSelectedDay(addDaysISO(calendarView.selectedDay, -1))}
                  aria-label="Previous day"
                >
                  ‹
                </button>
                <div className="h4 mb-0 fw-bold text-dark letter-spacing-n1" style={{ fontFamily: "var(--font-geist-sans), sans-serif" }}>
                  {dayHeaderLabel(calendarView.selectedDay)}
                </div>
                <button
                  className="btn btn-outline-secondary btn-sm rounded-circle d-flex align-items-center justify-content-center shadow-sm"
                  style={{ width: 32, height: 32 }}
                  onClick={() => calendarView.setSelectedDay(addDaysISO(calendarView.selectedDay, 1))}
                  aria-label="Next day"
                >
                  ›
                </button>
              </div>
            )}

            {/* Right: Search, Filter, Add & View Toggle */}
            <div className="d-flex align-items-center gap-2">
              {/* Loading indicator for background fetches */}
              {loading && (
                <div className="spinner-border spinner-border-sm text-secondary me-2" role="status">
                  <span className="visually-hidden">Loading...</span>
                </div>
              )}
              <FilterBar
                searchText={filters.searchText}
                setSearchText={filters.setSearchText}
                filterOpen={filters.filterOpen}
                setFilterOpen={filters.setFilterOpen}
                activeFilterCount={filters.activeFilterCount}
                kindFilter={filters.kindFilter}
                setKindFilter={filters.setKindFilter}
                fromDate={filters.fromDate}
                setFromDate={filters.setFromDate}
                toDate={filters.toDate}
                setToDate={filters.setToDate}
                locationFilter={filters.locationFilter}
                setLocationFilter={filters.setLocationFilter}
                selectedColors={filters.selectedColors}
                allColors={filters.allColors}
                toggleColor={filters.toggleColor}
                clearAllFilters={filters.clearAllFilters}
                onAddEvent={eventModal.openModal}
              />
              {calendarView.viewMode === "day" && (
                <button
                  className="btn btn-dark btn-sm rounded-pill px-4 fw-bold shadow-sm transition-all hover-scale"
                  onClick={() => calendarView.setViewMode("month")}
                  type="button"
                  style={{ fontSize: 12, height: 36 }}
                >
                  Month View
                </button>
              )}
            </div>
          </div>

          {/* ===== SWITCH MONTH / DAY ===== */}
          {calendarView.viewMode === "month" ? (
            <MonthGrid
              cells={calendarView.cells}
              onSelectDay={calendarView.setSelectedDay}
              setViewMode={calendarView.setViewMode}
            />
          ) : (
            <DayView
              dayEvents={calendarView.dayEvents}
            />
          )}

          {/* ===== HOTKEYS OVERLAY ===== */}
          <HotkeysModal isOpen={hotkeys.hotkeysOpen} onClose={() => hotkeys.setHotkeysOpen(false)} />

          {/* ===== CHAT MODAL ===== */}
          <ChatModal
            isOpen={chat.chatOpen}
            onClose={() => chat.setChatOpen(false)}
            sessions={chat.sessions}
            activeSessionId={chat.activeSessionId}
            setActiveSessionId={chat.setActiveSessionId}
            activeSession={chat.activeSession}
            chatInput={chat.chatInput}
            setChatInput={chat.setChatInput}
            pushUserMessage={chat.pushUserMessage}
            newSession={chat.newSession}
            isTyping={chat.isTyping}
            ttsEnabled={chat.ttsEnabled}
            toggleTts={chat.toggleTts}
            chatEndRef={chat.chatEndRef}
            isRecording={isRecording}
            toggleRecording={toggleRecording}
          />

          {/* ===== EVENT MODAL ===== */}
          <EventModal
            isOpen={eventModal.open}
            onClose={() => eventModal.setOpen(false)}
            mTitle={eventModal.mTitle}
            setMTitle={eventModal.setMTitle}
            modalKind={eventModal.modalKind}
            setModalKind={eventModal.setModalKind}
            saveEvent={saveEvent}
            mDate={eventModal.mDate}
            setMDate={eventModal.setMDate}
            mStart={eventModal.mStart}
            setMStart={eventModal.setMStart}
            mEnd={eventModal.mEnd}
            setMEnd={eventModal.setMEnd}
            mAllDay={eventModal.mAllDay}
            setMAllDay={eventModal.setMAllDay}
            mLocation={eventModal.mLocation}
            setMLocation={eventModal.setMLocation}
            mNotes={eventModal.mNotes}
            setMNotes={eventModal.setMNotes}
            mColor={eventModal.mColor}
            setMColor={eventModal.setMColor}
            minStart={eventModal.minStart}
            prettyDate={eventModal.prettyDate}
            realTodayKey={eventModal.realTodayKey}
            isTodaySelected={eventModal.isTodaySelected}
            events={events}
          />
        </main>
      </div>
    </div>
  );
}
